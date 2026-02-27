"""
Alert System - Discord and Email Notifications

Architecture:
  1. Discord Webhooks (instant notifications)
  2. Email via SMTP (detailed reports)
  3. Alert triggers (score threshold, structure events)
  4. Rate limiting (avoid spam)
  5. Alert history tracking

Purpose: Real-time notifications for high-confidence signals
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

from .scoring_engine import SignalScore, TradeDirection


class AlertConfig:
    """Configuration for alert system"""
    
    def __init__(
        self,
        discord_webhook_url: Optional[str] = None,
        email_smtp_server: str = "smtp.gmail.com",
        email_smtp_port: int = 587,
        email_from: Optional[str] = None,
        email_password: Optional[str] = None,
        email_to: Optional[List[str]] = None,
    ):
        """
        Initialize alert configuration
        
        Args:
            discord_webhook_url: Discord webhook URL (get from server settings)
            email_smtp_server: SMTP server (default: Gmail)
            email_smtp_port: SMTP port (default: 587 for TLS)
            email_from: Sender email address
            email_password: Email app password (not regular password!)
            email_to: List of recipient emails
        
        Environment Variables (alternative to passing params):
            DISCORD_WEBHOOK_URL
            EMAIL_FROM
            EMAIL_PASSWORD
            EMAIL_TO (comma-separated)
        """
        
        # Discord config
        self.discord_webhook_url = discord_webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        
        # Email config
        self.email_smtp_server = email_smtp_server
        self.email_smtp_port = email_smtp_port
        self.email_from = email_from or os.getenv('EMAIL_FROM')
        self.email_password = email_password or os.getenv('EMAIL_PASSWORD')
        
        email_to_env = os.getenv('EMAIL_TO')
        if email_to:
            self.email_to = email_to
        elif email_to_env:
            self.email_to = [e.strip() for e in email_to_env.split(',')]
        else:
            self.email_to = []
    
    def is_discord_enabled(self) -> bool:
        """Check if Discord is configured"""
        return bool(self.discord_webhook_url)
    
    def is_email_enabled(self) -> bool:
        """Check if Email is configured"""
        return bool(self.email_from and self.email_password and self.email_to)


class AlertSystem:
    """Send alerts via Discord and Email"""
    
    def __init__(self, config: AlertConfig):
        """
        Initialize alert system
        
        Args:
            config: AlertConfig with Discord/Email credentials
        """
        self.config = config
        self.alert_history = []  # Track sent alerts
        self.rate_limit_cache = {}  # Prevent duplicate alerts
    
    def send_signal_alert(
        self,
        signal: SignalScore,
        alert_reason: str = "High-confidence signal detected"
    ) -> bool:
        """
        Send alert for signal
        
        Args:
            signal: SignalScore object
            alert_reason: Why alert was triggered
        
        Returns:
            True if alert sent successfully
        """
        
        # Check rate limiting (max 1 alert per symbol per hour)
        cache_key = f"{signal.symbol}_{signal.direction.name}"
        last_alert = self.rate_limit_cache.get(cache_key)
        
        if last_alert and (datetime.now() - last_alert) < timedelta(hours=1):
            print(f"⏰ Rate limit: Skipping alert for {signal.symbol} (already alerted <1h ago)")
            return False
        
        # Send Discord alert
        discord_success = False
        if self.config.is_discord_enabled():
            discord_success = self._send_discord_alert(signal, alert_reason)
        
        # Send Email alert
        email_success = False
        if self.config.is_email_enabled():
            email_success = self._send_email_alert(signal, alert_reason)
        
        # Update cache
        if discord_success or email_success:
            self.rate_limit_cache[cache_key] = datetime.now()
            
            self.alert_history.append({
                'timestamp': datetime.now(),
                'symbol': signal.symbol,
                'direction': signal.direction.name,
                'score': signal.total_score,
                'reason': alert_reason,
                'discord': discord_success,
                'email': email_success,
            })
        
        return discord_success or email_success
    
    def _send_discord_alert(self, signal: SignalScore, reason: str) -> bool:
        """Send Discord webhook notification"""
        
        if not self.config.discord_webhook_url:
            return False
        
        # Determine color based on direction and score
        if signal.direction == TradeDirection.LONG:
            color = 0x28a745  # Green
            emoji = "🟢"
        else:
            color = 0xdc3545  # Red
            emoji = "🔴"
        
        # Build embed
        embed = {
            "title": f"{emoji} {signal.symbol} - {signal.direction.name} Signal",
            "description": reason,
            "color": color,
            "fields": [
                {
                    "name": "📊 Total Score",
                    "value": f"**{signal.total_score:.0f}/100**",
                    "inline": True
                },
                {
                    "name": "📈 Trend Strength",
                    "value": f"{signal.trend_strength:.0f}/100",
                    "inline": True
                },
                {
                    "name": "🎯 Confluence",
                    "value": f"{signal.direction_confluence:.0f}/100",
                    "inline": True
                },
                {
                    "name": "📊 Key Metrics",
                    "value": f"**ADX:** {signal.adx_value:.1f}\n**VR:** {signal.volume_ratio:.2f}\n**ATR%:** {signal.atr_pct:.2f}%",
                    "inline": False
                },
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "TradingAgents Alert System"
            }
        }
        
        # Add strengths
        if signal.strengths:
            strengths_text = "\n".join([f"✓ {s}" for s in signal.strengths[:3]])
            embed["fields"].append({
                "name": "✅ Strengths",
                "value": strengths_text,
                "inline": False
            })
        
        # Add weaknesses
        if signal.weaknesses:
            weaknesses_text = "\n".join([f"⚠️ {w}" for w in signal.weaknesses[:2]])
            embed["fields"].append({
                "name": "⚠️ Weaknesses",
                "value": weaknesses_text,
                "inline": False
            })
        
        # Send webhook
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.config.discord_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                print(f"✅ Discord alert sent: {signal.symbol} {signal.direction.name}")
                return True
            else:
                print(f"⚠️ Discord alert failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Discord error: {e}")
            return False
    
    def _send_email_alert(self, signal: SignalScore, reason: str) -> bool:
        """Send email notification"""
        
        if not self.config.is_email_enabled():
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 {signal.symbol} {signal.direction.name} Signal - Score {signal.total_score:.0f}/100"
        msg['From'] = self.config.email_from
        msg['To'] = ", ".join(self.config.email_to)
        
        # Plain text version
        text_content = f"""
TradingAgents Signal Alert

Symbol: {signal.symbol}
Direction: {signal.direction.name}
Score: {signal.total_score:.0f}/100

Reason: {reason}

Score Breakdown:
- Trend Strength: {signal.trend_strength:.0f}/100
- Direction Confluence: {signal.direction_confluence:.0f}/100
- Volume Quality: {signal.volume_quality:.0f}/100
- Structure Quality: {signal.structure_quality:.0f}/100
- Risk Profile: {signal.risk_profile:.0f}/100

Key Metrics:
- ADX: {signal.adx_value:.1f}
- Volume Ratio: {signal.volume_ratio:.2f}
- ATR%: {signal.atr_pct:.2f}%
- % from 200 SMA: {signal.pct_from_200sma:.1f}%

Strengths:
{chr(10).join([f"✓ {s}" for s in signal.strengths])}

Weaknesses:
{chr(10).join([f"⚠️ {w}" for w in signal.weaknesses]) if signal.weaknesses else "None significant"}

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # HTML version
        html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            background: {'#28a745' if signal.direction == TradeDirection.LONG else '#dc3545'};
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .score {{
            font-size: 2em;
            font-weight: bold;
        }}
        .metrics {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .strength {{
            color: #28a745;
        }}
        .weakness {{
            color: #dc3545;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #343a40;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{'🟢' if signal.direction == TradeDirection.LONG else '🔴'} {signal.symbol} {signal.direction.name} Signal</h1>
        <div class="score">Score: {signal.total_score:.0f}/100</div>
        <p>{reason}</p>
    </div>
    
    <div class="metrics">
        <h3>📊 Score Breakdown</h3>
        <table>
            <tr>
                <th>Component</th>
                <th>Score</th>
            </tr>
            <tr>
                <td>Trend Strength</td>
                <td><strong>{signal.trend_strength:.0f}/100</strong></td>
            </tr>
            <tr>
                <td>Direction Confluence</td>
                <td><strong>{signal.direction_confluence:.0f}/100</strong></td>
            </tr>
            <tr>
                <td>Volume Quality</td>
                <td><strong>{signal.volume_quality:.0f}/100</strong></td>
            </tr>
            <tr>
                <td>Structure Quality</td>
                <td><strong>{signal.structure_quality:.0f}/100</strong></td>
            </tr>
            <tr>
                <td>Risk Profile</td>
                <td><strong>{signal.risk_profile:.0f}/100</strong></td>
            </tr>
        </table>
    </div>
    
    <div class="metrics">
        <h3>📈 Key Metrics</h3>
        <ul>
            <li><strong>ADX:</strong> {signal.adx_value:.1f}</li>
            <li><strong>Volume Ratio:</strong> {signal.volume_ratio:.2f}</li>
            <li><strong>ATR%:</strong> {signal.atr_pct:.2f}%</li>
            <li><strong>% from 200 SMA:</strong> {signal.pct_from_200sma:.1f}%</li>
        </ul>
    </div>
    
    <div class="metrics">
        <h3 class="strength">✅ Strengths</h3>
        <ul>
            {''.join([f'<li class="strength">✓ {s}</li>' for s in signal.strengths])}
        </ul>
    </div>
    
    {'<div class="metrics"><h3 class="weakness">⚠️ Weaknesses</h3><ul>' + 
     ''.join([f'<li class="weakness">⚠️ {w}</li>' for w in signal.weaknesses]) + 
     '</ul></div>' if signal.weaknesses else ''}
    
    <p style="color: #6c757d; font-size: 0.9em; margin-top: 30px;">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        TradingAgents Alert System | Not financial advice
    </p>
</body>
</html>
"""
        
        # Attach both versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        try:
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_from, self.config.email_password)
            
            server.sendmail(
                self.config.email_from,
                self.config.email_to,
                msg.as_string()
            )
            
            server.quit()
            
            print(f"✅ Email alert sent: {signal.symbol} {signal.direction.name} to {len(self.config.email_to)} recipient(s)")
            return True
        
        except Exception as e:
            print(f"❌ Email error: {e}")
            return False
    
    def send_batch_alerts(
        self,
        signals: List[SignalScore],
        min_score: float = 75.0
    ) -> int:
        """
        Send alerts for multiple signals above threshold
        
        Args:
            signals: List of SignalScore objects
            min_score: Minimum score to trigger alert
        
        Returns:
            Number of alerts sent
        """
        
        alerts_sent = 0
        
        for signal in signals:
            if signal.total_score >= min_score:
                success = self.send_signal_alert(
                    signal,
                    f"Score {signal.total_score:.0f}/100 exceeds threshold {min_score:.0f}"
                )
                if success:
                    alerts_sent += 1
        
        return alerts_sent
    
    def send_daily_summary(
        self,
        signals: List[SignalScore],
        report_path: Optional[str] = None
    ) -> bool:
        """
        Send daily summary email with all signals
        
        Args:
            signals: All signals from daily scan
            report_path: Path to HTML report (optional attachment)
        
        Returns:
            True if sent successfully
        """
        
        if not self.config.is_email_enabled():
            print("⚠️ Email not configured for daily summary")
            return False
        
        # Filter high-quality signals
        high_quality = [s for s in signals if s.total_score >= 70]
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f"📊 Daily Trading Summary - {len(high_quality)} Strong Signals"
        msg['From'] = self.config.email_from
        msg['To'] = ", ".join(self.config.email_to)
        
        # Summary text
        text = f"""
Daily Trading Summary - {datetime.now().strftime('%Y-%m-%d')}

Total Signals Analyzed: {len(signals)}
Strong Signals (70+): {len(high_quality)}

Top 5 Signals:
"""
        
        # Sort by score
        sorted_signals = sorted(signals, key=lambda s: s.total_score, reverse=True)
        
        for i, sig in enumerate(sorted_signals[:5], 1):
            text += f"\n{i}. {sig.symbol} {sig.direction.name} - {sig.total_score:.0f}/100"
        
        text += "\n\nSee attached HTML report for full details."
        
        msg.attach(MIMEText(text, 'plain'))
        
        # Attach HTML report if provided
        if report_path and os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{os.path.basename(report_path)}"'
                )
                msg.attach(part)
        
        # Send
        try:
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_from, self.config.email_password)
            
            server.sendmail(
                self.config.email_from,
                self.config.email_to,
                msg.as_string()
            )
            
            server.quit()
            
            print(f"✅ Daily summary sent to {len(self.config.email_to)} recipient(s)")
            return True
        
        except Exception as e:
            print(f"❌ Email error: {e}")
            return False
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """Get alert history for last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alert_history if a['timestamp'] > cutoff]


# ==================== EXAMPLE USAGE ====================

def example_send_alerts():
    """Example: Configure and send alerts"""
    
    # Configure (use environment variables or pass directly)
    config = AlertConfig(
        # discord_webhook_url="YOUR_WEBHOOK_URL",  # or set DISCORD_WEBHOOK_URL env var
        # email_from="your@email.com",             # or set EMAIL_FROM env var
        # email_password="your_app_password",      # or set EMAIL_PASSWORD env var
        # email_to=["recipient@email.com"],        # or set EMAIL_TO env var
    )
    
    alert_system = AlertSystem(config)
    
    print(f"\n📧 Alert System Configuration:")
    print(f"   Discord: {'✓ Enabled' if config.is_discord_enabled() else '✗ Disabled'}")
    print(f"   Email: {'✓ Enabled' if config.is_email_enabled() else '✗ Disabled'}")
    
    # Example: Create mock signal
    from .scoring_engine import SignalScore, TradeDirection
    
    mock_signal = SignalScore(
        symbol="AAPL",
        direction=TradeDirection.LONG,
        total_score=82.0,
        trend_strength=85.0,
        direction_confluence=90.0,
        volume_quality=75.0,
        structure_quality=70.0,
        risk_profile=80.0,
        adx_value=38.0,
        volume_ratio=1.75,
        pct_from_200sma=3.5,
        atr_pct=1.8,
        weekly_trend=1,
        strengths=["Very strong trend (ADX 38)", "Weekly bull regime", "High volume confirmation"],
        weaknesses=[],
    )
    
    # Send alert
    if config.is_discord_enabled() or config.is_email_enabled():
        alert_system.send_signal_alert(mock_signal, "High-confidence LONG setup detected")
    else:
        print("\n⚠️ No alert channels configured. Set environment variables:")
        print("   - DISCORD_WEBHOOK_URL (for Discord)")
        print("   - EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO (for Email)")


if __name__ == "__main__":
    example_send_alerts()
