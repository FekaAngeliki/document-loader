"""
Azure Functions implementation for scheduled SharePoint delta sync
This provides a serverless approach to running document synchronization
"""

import azure.functions as func
import subprocess
import logging
import os
import json
import smtplib
from datetime import datetime, timezone
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp()

class DocumentLoaderSync:
    """Handles the document loader synchronization process"""
    
    def __init__(self):
        self.sync_start_time = None
        self.sync_end_time = None
        self.sync_results = {}
        
    def get_secrets_from_keyvault(self):
        """Retrieve secrets from Azure Key Vault"""
        try:
            key_vault_url = os.environ.get('KEY_VAULT_URL')
            if not key_vault_url:
                logger.warning("KEY_VAULT_URL not set, using environment variables directly")
                return self.get_env_variables()
            
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=key_vault_url, credential=credential)
            
            secrets = {
                'SHAREPOINT_TENANT_ID': client.get_secret('sharepoint-tenant-id').value,
                'SHAREPOINT_CLIENT_ID': client.get_secret('sharepoint-client-id').value,
                'SHAREPOINT_CLIENT_SECRET': client.get_secret('sharepoint-client-secret').value,
                'DOCUMENT_LOADER_DB_HOST': client.get_secret('db-host').value,
                'DOCUMENT_LOADER_DB_NAME': client.get_secret('db-name').value,
                'DOCUMENT_LOADER_DB_USER': client.get_secret('db-user').value,
                'DOCUMENT_LOADER_DB_PASSWORD': client.get_secret('db-password').value,
            }
            
            logger.info("Successfully retrieved secrets from Key Vault")
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to retrieve secrets from Key Vault: {e}")
            logger.info("Falling back to environment variables")
            return self.get_env_variables()
    
    def get_env_variables(self):
        """Get configuration from environment variables"""
        return {
            'SHAREPOINT_TENANT_ID': os.environ.get('SHAREPOINT_TENANT_ID'),
            'SHAREPOINT_CLIENT_ID': os.environ.get('SHAREPOINT_CLIENT_ID'),
            'SHAREPOINT_CLIENT_SECRET': os.environ.get('SHAREPOINT_CLIENT_SECRET'),
            'DOCUMENT_LOADER_DB_HOST': os.environ.get('DOCUMENT_LOADER_DB_HOST'),
            'DOCUMENT_LOADER_DB_NAME': os.environ.get('DOCUMENT_LOADER_DB_NAME'),
            'DOCUMENT_LOADER_DB_USER': os.environ.get('DOCUMENT_LOADER_DB_USER'),
            'DOCUMENT_LOADER_DB_PASSWORD': os.environ.get('DOCUMENT_LOADER_DB_PASSWORD'),
        }
    
    def validate_configuration(self, env_vars):
        """Validate that all required configuration is present"""
        required_vars = [
            'SHAREPOINT_TENANT_ID', 'SHAREPOINT_CLIENT_ID', 'SHAREPOINT_CLIENT_SECRET',
            'DOCUMENT_LOADER_DB_HOST', 'DOCUMENT_LOADER_DB_NAME', 
            'DOCUMENT_LOADER_DB_USER', 'DOCUMENT_LOADER_DB_PASSWORD'
        ]
        
        missing_vars = [var for var in required_vars if not env_vars.get(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info("Configuration validation passed")
    
    def execute_sync(self, knowledge_base_name="PremiumRMs-kb"):
        """Execute the document loader synchronization"""
        
        logger.info(f"Starting SharePoint delta sync for KB: {knowledge_base_name}")
        self.sync_start_time = datetime.now(timezone.utc)
        
        # Get configuration
        env_vars = self.get_secrets_from_keyvault()
        self.validate_configuration(env_vars)
        
        try:
            # Execute the sync command
            cmd = [
                'document-loader', 
                'multi-source', 
                'sync-kb', 
                knowledge_base_name,
                '--sync-mode', 'parallel'
            ]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env={**os.environ, **env_vars},
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            self.sync_end_time = datetime.now(timezone.utc)
            duration = (self.sync_end_time - self.sync_start_time).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"Sync completed successfully in {duration:.1f} seconds")
                self.sync_results = {
                    'status': 'success',
                    'duration_seconds': duration,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
            else:
                logger.error(f"Sync failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                self.sync_results = {
                    'status': 'failed',
                    'duration_seconds': duration,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            self.sync_end_time = datetime.now(timezone.utc)
            duration = (self.sync_end_time - self.sync_start_time).total_seconds()
            logger.error(f"Sync timed out after {duration:.1f} seconds")
            self.sync_results = {
                'status': 'timeout',
                'duration_seconds': duration,
                'stdout': '',
                'stderr': 'Process timed out after 1 hour',
                'return_code': -1
            }
            
        except Exception as e:
            self.sync_end_time = datetime.now(timezone.utc)
            duration = (self.sync_end_time - self.sync_start_time).total_seconds()
            logger.error(f"Sync failed with exception: {str(e)}")
            self.sync_results = {
                'status': 'error',
                'duration_seconds': duration,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }
        
        return self.sync_results
    
    def get_sync_statistics(self):
        """Get sync statistics from the database"""
        try:
            env_vars = self.get_secrets_from_keyvault()
            
            cmd = [
                'document-loader',
                'db',
                'sync-runs',
                '--limit', '1',
                '--detailed'
            ]
            
            result = subprocess.run(
                cmd,
                env={**os.environ, **env_vars},
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"Failed to get sync statistics: {result.stderr}")
                return "Statistics unavailable"
                
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return "Statistics unavailable"
    
    def store_results_in_blob(self):
        """Store sync results in Azure Blob Storage for audit purposes"""
        try:
            storage_connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            if not storage_connection_string:
                logger.info("Azure Storage not configured, skipping result storage")
                return
            
            blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
            container_name = "sync-results"
            
            # Create blob name with timestamp
            timestamp = self.sync_start_time.strftime("%Y%m%d_%H%M%S")
            blob_name = f"sharepoint_sync_{timestamp}.json"
            
            # Prepare result data
            result_data = {
                'knowledge_base': 'PremiumRMs-kb',
                'sync_start_time': self.sync_start_time.isoformat(),
                'sync_end_time': self.sync_end_time.isoformat(),
                'results': self.sync_results,
                'statistics': self.get_sync_statistics()
            }
            
            # Upload to blob storage
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            blob_client.upload_blob(
                json.dumps(result_data, indent=2),
                blob_type="BlockBlob",
                overwrite=True
            )
            
            logger.info(f"Sync results stored in blob: {blob_name}")
            
        except Exception as e:
            logger.error(f"Failed to store results in blob storage: {e}")
    
    def send_notification(self):
        """Send email notification about sync results"""
        try:
            # Email configuration
            smtp_server = os.environ.get('SMTP_SERVER', 'smtp.office365.com')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            smtp_username = os.environ.get('SMTP_USERNAME')
            smtp_password = os.environ.get('SMTP_PASSWORD')
            notification_emails = os.environ.get('NOTIFICATION_EMAILS', '').split(',')
            
            if not all([smtp_username, smtp_password]) or not notification_emails[0]:
                logger.info("Email configuration incomplete, skipping notification")
                return
            
            # Prepare email content
            status = self.sync_results.get('status', 'unknown')
            duration = self.sync_results.get('duration_seconds', 0)
            
            subject = f"SharePoint Delta Sync - {status.title()} - {self.sync_start_time.strftime('%Y-%m-%d %H:%M')} UTC"
            
            body = f"""
SharePoint Delta Sync Execution Report

Knowledge Base: PremiumRMs-kb
Execution Time: {self.sync_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
Duration: {duration:.1f} seconds
Status: {status.title()}

Source: SharePoint Enterprise (https://groupnbg.sharepoint.com/sites/div991secb)

{self.get_sync_statistics()}

System Output:
{self.sync_results.get('stdout', '')[:1000]}

{'Errors:' if self.sync_results.get('stderr') else ''}
{self.sync_results.get('stderr', '')[:500]}

This is an automated message from the Document Loader Azure Function.
Function Name: {os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT', 'document-loader-sync')}
"""
            
            # Create and send email
            msg = MimeMultipart()
            msg['From'] = smtp_username
            msg['To'] = ', '.join(notification_emails)
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Notification sent to: {', '.join(notification_emails)}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

@app.timer_trigger(schedule="0 2 * * *", arg_name="timer", run_on_startup=False)
def scheduled_sharepoint_sync(timer: func.TimerRequest) -> None:
    """
    Azure Function timer trigger for scheduled SharePoint delta sync
    
    Schedule: Daily at 2:00 AM UTC (4:00 AM Greece time in winter)
    Cron format: "0 2 * * *"
    
    Alternative schedules:
    - "0 */6 * * *"     # Every 6 hours
    - "0 8,14,20 * * *" # Three times daily
    - "0 2 * * 1-5"     # Weekdays only
    """
    
    utc_timestamp = datetime.utcnow().isoformat()
    
    if timer.past_due:
        logger.warning(f'Timer trigger is past due at {utc_timestamp}')
    
    logger.info(f'SharePoint delta sync timer trigger executed at {utc_timestamp}')
    
    # Execute synchronization
    sync_handler = DocumentLoaderSync()
    
    try:
        # Run the sync
        results = sync_handler.execute_sync()
        
        # Store results for audit
        sync_handler.store_results_in_blob()
        
        # Send notification
        sync_handler.send_notification()
        
        logger.info(f'Scheduled sync execution completed with status: {results["status"]}')
        
    except Exception as e:
        logger.error(f'Scheduled sync execution failed: {str(e)}')
        raise

@app.http_trigger(route="manual-sync", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def manual_sharepoint_sync(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger for manual SharePoint delta sync execution
    
    POST /api/manual-sync
    
    Optional JSON body:
    {
        "knowledge_base": "PremiumRMs-kb",
        "sync_mode": "parallel"
    }
    """
    
    logger.info('Manual SharePoint sync HTTP trigger executed')
    
    try:
        # Parse request body
        request_body = {}
        try:
            req_body = req.get_json()
            if req_body:
                request_body = req_body
        except ValueError:
            pass
        
        knowledge_base = request_body.get('knowledge_base', 'PremiumRMs-kb')
        
        # Execute synchronization
        sync_handler = DocumentLoaderSync()
        results = sync_handler.execute_sync(knowledge_base)
        
        # Store results
        sync_handler.store_results_in_blob()
        
        # Prepare response
        response_data = {
            'status': results['status'],
            'knowledge_base': knowledge_base,
            'duration_seconds': results['duration_seconds'],
            'sync_start_time': sync_handler.sync_start_time.isoformat(),
            'sync_end_time': sync_handler.sync_end_time.isoformat(),
            'message': 'Sync completed successfully' if results['status'] == 'success' else 'Sync completed with errors'
        }
        
        status_code = 200 if results['status'] == 'success' else 500
        
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f'Manual sync execution failed: {str(e)}')
        
        error_response = {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )

@app.http_trigger(route="sync-status", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_sync_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger to get last sync status and statistics
    
    GET /api/sync-status
    """
    
    logger.info('Sync status HTTP trigger executed')
    
    try:
        sync_handler = DocumentLoaderSync()
        statistics = sync_handler.get_sync_statistics()
        
        response_data = {
            'status': 'available',
            'last_sync_statistics': statistics,
            'timestamp': datetime.utcnow().isoformat(),
            'knowledge_base': 'PremiumRMs-kb'
        }
        
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f'Failed to get sync status: {str(e)}')
        
        error_response = {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )