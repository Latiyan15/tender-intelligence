"""
Email Notification Service for Nikom Tender Intelligence
Dispatches 24h tender digests and immediate alerts to the bidding team.
Supports live SMTP delivery (Gmail, Outlook, custom relay) and graceful offline preview.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def load_env_vars():
    """Loads key=value pairs from .env if present in root directory."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")
        except Exception as e:
            logger.warning(f"Failed to read .env file: {e}")


class EmailService:
    def __init__(self, recipient: Optional[str] = None):
        load_env_vars()
        self.recipient = recipient or os.environ.get("ALERT_RECIPIENT_EMAIL", "nikominfrasolutionsss@gmail.com")
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.smtp_from = os.environ.get("SMTP_FROM", f"Nikom Tender Intelligence <{self.smtp_user or 'nikominfrasolutionsss@gmail.com'}>")

    def is_smtp_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_pass)

    def generate_digest_html(
        self,
        tenders: List[Dict[str, Any]],
        window_label: str = "Past 24 Hours",
        recipient_name: str = "Bidding Team"
    ) -> str:
        """
        Generates an executive, responsive HTML email matching Nikom's corporate identity.
        """
        tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        total_value = 0.0

        for t in tenders:
            tier = (t.get("highest_tier") or "D").upper()
            if tier in tier_counts:
                tier_counts[tier] += 1
            cost = t.get("estimated_cost_inr") or 0.0
            if cost:
                total_value += cost

        # Top 15 priority tenders by value/date
        sorted_tenders = sorted(
            tenders,
            key=lambda x: (x.get("highest_tier") == "A", x.get("estimated_cost_inr") or 0),
            reverse=True
        )[:15]

        tier_badges = {
            "A": '<span style="background: rgba(239, 68, 68, 0.15); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.3); padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">Tier A • Cyber Security</span>',
            "B": '<span style="background: rgba(59, 130, 246, 0.15); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.3); padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">Tier B • IT Infrastructure</span>',
            "C": '<span style="background: rgba(16, 185, 129, 0.15); color: #059669; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">Tier C • Cloud & DR</span>',
            "D": '<span style="background: rgba(139, 92, 246, 0.15); color: #7c3aed; border: 1px solid rgba(139, 92, 246, 0.3); padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">Tier D • DC Facility & Services</span>',
        }

        rows_html = ""
        for idx, t in enumerate(sorted_tenders, 1):
            tier = (t.get("highest_tier") or "D").upper()
            badge = tier_badges.get(tier, tier_badges["D"])
            tid = t.get("tender_id") or ""
            ref = t.get("reference_no") or tid
            title = t.get("title") or "Untitled Tender"
            auth = t.get("authority") or "Unknown Buyer"
            src = (t.get("portal_source") or "CPPP").upper()
            cost = t.get("estimated_cost_inr")
            cost_str = f"₹ {cost:,.2f}" if cost else "Refer BOQ / Item Rate"
            deadline = t.get("submission_deadline") or "Check Portal"

            rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
              <td style="padding: 12px 10px; vertical-align: top; text-align: center; color: #64748b; font-weight: 600;">{idx}</td>
              <td style="padding: 12px 10px; vertical-align: top;">
                <div style="margin-bottom: 4px;">{badge}</div>
                <div style="font-weight: 700; color: #0f172a; line-height: 1.35; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 11.5px; color: #64748b;">Buyer: <strong style="color: #334155;">{auth}</strong> | Source: <strong style="color: #334155;">{src}</strong></div>
              </td>
              <td style="padding: 12px 10px; vertical-align: top; font-family: monospace; font-size: 12px; color: #334155;">
                <div>{ref}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">{tid}</div>
              </td>
              <td style="padding: 12px 10px; vertical-align: top; white-space: nowrap;">
                <div style="font-weight: 700; color: #0f172a;">{cost_str}</div>
                <div style="font-size: 11.5px; color: #e11d48; margin-top: 3px;">Due: {deadline[:10] if len(deadline) >= 10 else deadline}</div>
              </td>
              <td style="padding: 12px 10px; vertical-align: middle; text-align: center; white-space: nowrap;">
                <a href="http://127.0.0.1:8000/api/portal/bridge?tender_id={tid}" target="_blank" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 6px 12px; border-radius: 5px; font-weight: 600; font-size: 11px;">View Portal ↗</a>
              </td>
            </tr>
            """

        generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p IST")

        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Nikom Tender Intelligence Daily Digest</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <div style="max-width: 820px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 28px 32px; color: #ffffff;">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; color: #38bdf8; font-weight: 700; margin-bottom: 4px;">Nikom Tender Intelligence • Bidding Radar</div>
          <h1 style="font-size: 22px; margin: 0; font-weight: 800; color: #ffffff;">New Opportunities Digest ({window_label})</h1>
        </div>
      </div>
      <div style="margin-top: 14px; font-size: 12.5px; color: #94a3b8;">
        Target Recipient: <strong style="color: #ffffff;">{self.recipient}</strong> | Dispatched: <strong style="color: #ffffff;">{generated_at}</strong>
      </div>
    </div>

    <!-- Summary KPI Cards -->
    <div style="padding: 24px 32px 16px 32px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 10px; width: 20%; text-align: center; background: #ffffff; border-radius: 8px; border: 1px solid #cbd5e1;">
            <div style="font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase;">Total Verified</div>
            <div style="font-size: 24px; font-weight: 800; color: #0f172a; margin-top: 2px;">{len(tenders)}</div>
          </td>
          <td style="width: 1%;"></td>
          <td style="padding: 10px; width: 20%; text-align: center; background: #ffffff; border-radius: 8px; border: 1px solid #fca5a5;">
            <div style="font-size: 11px; color: #dc2626; font-weight: 600; text-transform: uppercase;">Cyber Security</div>
            <div style="font-size: 24px; font-weight: 800; color: #dc2626; margin-top: 2px;">{tier_counts['A']}</div>
          </td>
          <td style="width: 1%;"></td>
          <td style="padding: 10px; width: 20%; text-align: center; background: #ffffff; border-radius: 8px; border: 1px solid #93c5fd;">
            <div style="font-size: 11px; color: #2563eb; font-weight: 600; text-transform: uppercase;">IT Infra</div>
            <div style="font-size: 24px; font-weight: 800; color: #2563eb; margin-top: 2px;">{tier_counts['B']}</div>
          </td>
          <td style="width: 1%;"></td>
          <td style="padding: 10px; width: 20%; text-align: center; background: #ffffff; border-radius: 8px; border: 1px solid #6ee7b7;">
            <div style="font-size: 11px; color: #059669; font-weight: 600; text-transform: uppercase;">Cloud / DR</div>
            <div style="font-size: 24px; font-weight: 800; color: #059669; margin-top: 2px;">{tier_counts['C']}</div>
          </td>
          <td style="width: 1%;"></td>
          <td style="padding: 10px; width: 20%; text-align: center; background: #ffffff; border-radius: 8px; border: 1px solid #c4b5fd;">
            <div style="font-size: 11px; color: #7c3aed; font-weight: 600; text-transform: uppercase;">DC Facilities</div>
            <div style="font-size: 24px; font-weight: 800; color: #7c3aed; margin-top: 2px;">{tier_counts['D']}</div>
          </td>
        </tr>
      </table>
    </div>

    <!-- Instructions / Next Steps -->
    <div style="padding: 16px 32px; background: #fffbeb; border-bottom: 1px solid #fef3c7; font-size: 12.5px; color: #92400e;">
      <strong>Human Verification Required:</strong> Please inspect the opportunities below. Click <em>View Portal</em> to download the official tender pack and upload the primary NIT document for automated Qualify, Decide & Proposal Draft generation.
    </div>

    <!-- Table of Top Opportunities -->
    <div style="padding: 24px 32px;">
      <h3 style="font-size: 15px; margin: 0 0 14px 0; color: #0f172a;">Priority Bidding Opportunities (Top {len(sorted_tenders)} by Scope & Value)</h3>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; font-size: 11px; text-transform: uppercase; color: #475569;">
            <th style="padding: 10px; width: 5%; text-align: center;">#</th>
            <th style="padding: 10px; width: 45%;">Tender Title & Authority</th>
            <th style="padding: 10px; width: 20%;">Reference / ID</th>
            <th style="padding: 10px; width: 18%;">Value & Due Date</th>
            <th style="padding: 10px; width: 12%; text-align: center;">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 11.5px; color: #94a3b8; text-align: center;">
      Nikom InfraSolutions Pvt. Ltd. • Turnkey Data Centers & Enterprise IT Procurement Intelligence<br>
      Automated intelligence dispatch sent to <strong>{self.recipient}</strong>. You can configure alert cadences in Dashboard Settings.
    </div>
  </div>
</body>
</html>
        """
        return html

    def send_email(
        self,
        subject: str,
        html_content: str,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempts live delivery via SMTP if configured.
        If SMTP credentials are not configured, records the email to reports/emails for preview.
        """
        target_to = recipient or self.recipient

        # If SMTP credentials are provided, attempt live delivery
        if self.smtp_user and self.smtp_pass:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.smtp_from
                msg["To"] = target_to

                part = MIMEText(html_content, "html", "utf-8")
                msg.attach(part)

                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=12) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_from, [target_to], msg.as_string())

                logger.info(f"Successfully dispatched live email alert to {target_to}")
                return {
                    "success": True,
                    "mode": "live_smtp",
                    "recipient": target_to,
                    "subject": subject,
                    "message": f"Live email successfully delivered to {target_to}"
                }
            except Exception as e:
                logger.error(f"SMTP delivery failed: {e}")
                os.makedirs("reports/emails", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_to = target_to.replace("@", "_at_").replace(".", "_")
                filename = f"reports/emails/digest_{safe_to}_{timestamp}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                return {
                    "success": False,
                    "mode": "smtp_failed",
                    "error": str(e),
                    "recipient": target_to,
                    "subject": subject,
                    "preview_path": filename,
                    "message": f"SMTP transmission failed ({e}). Saved email preview to {filename}"
                }

        # Otherwise, save preview to reports/emails for auditing and inspection
        os.makedirs("reports/emails", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_to = target_to.replace("@", "_at_").replace(".", "_")
        filename = f"reports/emails/digest_{safe_to}_{timestamp}.html"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        return {
            "success": True,
            "mode": "preview_recorded",
            "recipient": target_to,
            "subject": subject,
            "preview_path": filename,
            "message": f"Email alert generated in Preview Mode (No SMTP sender configured). Saved to {filename}"
        }
