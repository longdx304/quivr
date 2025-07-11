"""
Utility functions for ETL pipeline
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import json
import time

# Optional email imports (for notifications)
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("Email functionality not available - notifications will be logged only")

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # Add file logger
    logger.add(
        "etl_logs/etl_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="1 day",
        retention="30 days",
        compression="gz"
    )
    
    # Create logs directory if it doesn't exist
    os.makedirs("etl_logs", exist_ok=True)
    
    logger.info(f"Logging setup complete - Level: {log_level}")

def send_notification(execution_id: str, success: bool, stats: Dict[str, Any], 
                     error_message: Optional[str] = None):
    """Send notification about ETL execution"""
    
    # Email notification (if configured)
    email_config = _get_email_config()
    if email_config:
        _send_email_notification(execution_id, success, stats, error_message, email_config)
    
    # Slack notification (if configured)
    slack_config = _get_slack_config()
    if slack_config:
        _send_slack_notification(execution_id, success, stats, error_message, slack_config)
    
    # Log notification
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"ETL Execution {execution_id} completed with status: {status}")

def _get_email_config() -> Optional[Dict[str, str]]:
    """Get email configuration from environment"""
    config = {
        'smtp_server': os.getenv('ETL_SMTP_SERVER'),
        'smtp_port': os.getenv('ETL_SMTP_PORT', '587'),
        'username': os.getenv('ETL_SMTP_USERNAME'),
        'password': os.getenv('ETL_SMTP_PASSWORD'),
        'from_email': os.getenv('ETL_FROM_EMAIL'),
        'to_emails': os.getenv('ETL_TO_EMAILS', '').split(',')
    }
    
    # Check if all required fields are present
    if all([config['smtp_server'], config['username'], config['password'], 
            config['from_email'], config['to_emails'][0]]):
        return config
    return None

def _get_slack_config() -> Optional[Dict[str, str]]:
    """Get Slack configuration from environment"""
    webhook_url = os.getenv('ETL_SLACK_WEBHOOK_URL')
    return {'webhook_url': webhook_url} if webhook_url else None

def _send_email_notification(execution_id: str, success: bool, stats: Dict[str, Any],
                           error_message: Optional[str], config: Dict[str, str]):
    """Send email notification"""
    if not EMAIL_AVAILABLE:
        logger.warning("Email not available - skipping email notification")
        return
    
    try:
        # Create message
        msg = MimeMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ', '.join(config['to_emails'])
        msg['Subject'] = f"ETL Pipeline {execution_id} - {'SUCCESS' if success else 'FAILED'}"
        
        # Create body
        body = _create_email_body(execution_id, success, stats, error_message)
        msg.attach(MimeText(body, 'html'))
        
        # Send email
        server = smtplib.SMTP(config['smtp_server'], int(config['smtp_port']))
        server.starttls()
        server.login(config['username'], config['password'])
        text = msg.as_string()
        server.sendmail(config['from_email'], config['to_emails'], text)
        server.quit()
        
        logger.info(f"Email notification sent for execution {execution_id}")
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

def _send_slack_notification(execution_id: str, success: bool, stats: Dict[str, Any],
                           error_message: Optional[str], config: Dict[str, str]):
    """Send Slack notification"""
    try:
        import requests
        
        status = "SUCCESS ✅" if success else "FAILED ❌"
        color = "good" if success else "danger"
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"ETL Pipeline {status}",
                    "fields": [
                        {"title": "Execution ID", "value": execution_id, "short": True},
                        {"title": "Status", "value": status, "short": True},
                        {"title": "Total Tables", "value": str(stats['total_tables']), "short": True},
                        {"title": "Successful", "value": str(stats['successful_tables']), "short": True},
                        {"title": "Failed", "value": str(stats['failed_tables']), "short": True},
                        {"title": "Total Records", "value": str(stats['total_records']), "short": True},
                        {"title": "Execution Time", "value": f"{stats['execution_time']:.2f}s", "short": True}
                    ],
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        if error_message:
            payload["attachments"][0]["fields"].append({
                "title": "Error",
                "value": error_message[:500] + "..." if len(error_message) > 500 else error_message,
                "short": False
            })
        
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
        
        logger.info(f"Slack notification sent for execution {execution_id}")
        
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")

def _create_email_body(execution_id: str, success: bool, stats: Dict[str, Any],
                      error_message: Optional[str]) -> str:
    """Create HTML email body"""
    
    status = "SUCCESS" if success else "FAILED"
    status_color = "#28a745" if success else "#dc3545"
    
    html = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {status_color}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }}
                .stats-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .stats-table th {{ background-color: #f2f2f2; }}
                .error {{ background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>ETL Pipeline Execution Report</h2>
                <p>Execution ID: {execution_id}</p>
                <p>Status: {status}</p>
            </div>
            
            <div class="content">
                <h3>Execution Statistics</h3>
                <table class="stats-table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Tables</td><td>{stats['total_tables']}</td></tr>
                    <tr><td>Successful Tables</td><td>{stats['successful_tables']}</td></tr>
                    <tr><td>Failed Tables</td><td>{stats['failed_tables']}</td></tr>
                    <tr><td>Total Records Processed</td><td>{stats['total_records']:,}</td></tr>
                    <tr><td>Execution Time</td><td>{stats['execution_time']:.2f} seconds</td></tr>
                    <tr><td>Records per Second</td><td>{stats['total_records'] / max(stats['execution_time'], 1):.2f}</td></tr>
                </table>
                
                <h3>Execution Details</h3>
                <p><strong>Start Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                <p><strong>Success Rate:</strong> {(stats['successful_tables'] / max(stats['total_tables'], 1) * 100):.1f}%</p>
    """
    
    if error_message:
        html += f"""
                <div class="error">
                    <h4>Error Details:</h4>
                    <p>{error_message}</p>
                </div>
        """
    
    html += """
            </div>
        </body>
    </html>
    """
    
    return html

def create_execution_report(execution_id: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """Create detailed execution report"""
    
    report = {
        'execution_id': execution_id,
        'timestamp': datetime.utcnow().isoformat(),
        'statistics': stats,
        'performance_metrics': {
            'records_per_second': stats['total_records'] / max(stats['execution_time'], 1),
            'success_rate': (stats['successful_tables'] / max(stats['total_tables'], 1)) * 100,
            'avg_time_per_table': stats['execution_time'] / max(stats['total_tables'], 1)
        },
        'status': 'SUCCESS' if stats['failed_tables'] == 0 else 'FAILED'
    }
    
    return report

def save_execution_report(report: Dict[str, Any], output_dir: str = "etl_reports"):
    """Save execution report to file"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"etl_report_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Execution report saved to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save execution report: {e}")

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds:.1f}s"

def validate_configuration() -> bool:
    """Validate ETL configuration"""
    try:
        from .config import db_config, etl_config
        
        # Check database configurations
        required_db_configs = [
            'SUPABASE_HOST', 'SUPABASE_PORT', 'SUPABASE_USER', 'SUPABASE_PASSWORD',
            'SQLSERVER_HOST', 'SQLSERVER_PORT', 'SQLSERVER_USER', 'SQLSERVER_PASSWORD'
        ]
        
        for config_name in required_db_configs:
            value = getattr(db_config, config_name, None)
            if not value:
                logger.error(f"Missing required configuration: {config_name}")
                return False
        
        # Check ETL configurations
        if not etl_config.SYNC_TABLES:
            logger.error("No tables configured for synchronization")
            return False
        
        logger.info("Configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

def get_database_health() -> Dict[str, Any]:
    """Get database health status"""
    health = {
        'supabase': {'status': 'unknown', 'response_time': 0},
        'sqlserver': {'status': 'unknown', 'response_time': 0}
    }
    
    # Test Supabase
    try:
        from .database import supabase_conn
        start_time = time.time()
        with supabase_conn.get_session() as session:
            session.execute("SELECT 1")
        health['supabase']['status'] = 'healthy'
        health['supabase']['response_time'] = time.time() - start_time
    except Exception as e:
        health['supabase']['status'] = f'unhealthy: {str(e)}'
    
    # Test SQL Server
    try:
        from .database import sqlserver_conn
        start_time = time.time()
        sqlserver_conn.test_connection()
        health['sqlserver']['status'] = 'healthy'
        health['sqlserver']['response_time'] = time.time() - start_time
    except Exception as e:
        health['sqlserver']['status'] = f'unhealthy: {str(e)}'
    
    return health 