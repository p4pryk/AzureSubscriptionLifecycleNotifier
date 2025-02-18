import requests
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

# SPN Data
tenant_id = "<TENANT_ID>"
client_id = "<CLIENT_ID>"
client_secret = "<CLIENT_SECRET>"

# Endpoints
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
subscriptions_url = "https://management.azure.com/subscriptions?api-version=2020-01-01"
subscription_tags_url_template = "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Resources/tags/default?api-version=2021-04-01"

# Obtain access token
def get_access_token(scope="https://graph.microsoft.com/.default"):
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope
    }
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error obtaining token:", response.json())
        return None

# List subscriptions
def list_subscriptions(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(subscriptions_url, headers=headers)
    print("Response Status:", response.status_code)
    print("Response JSON:", response.json())
    if response.status_code == 200:
        subscriptions = response.json().get("value", [])
        return [{"id": sub["subscriptionId"], "name": sub["displayName"]} for sub in subscriptions]
    else:
        print("Error fetching subscription list:", response.json())
        return []

# Retrieve tags assigned to a subscription
def get_subscription_tags(access_token, subscription_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    subscription_tags_url = subscription_tags_url_template.format(subscription_id=subscription_id)
    response = requests.get(subscription_tags_url, headers=headers)
    if response.status_code == 200:
        tags_data = response.json().get("properties", {}).get("tags", {})
        return tags_data
    else:
        print(f"Error fetching tags for subscription {subscription_id}:", response.json())
        return {}

# Add or update a tag in a subscription
def add_or_update_subscription_tag(access_token, subscription_id, tag_key, tag_value):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    subscription_tags_url = subscription_tags_url_template.format(subscription_id=subscription_id)

    # Retrieve current tags
    current_tags = get_subscription_tags(access_token, subscription_id)
    current_tags[tag_key] = tag_value  # Add or update tag

    payload = {
        "properties": {
            "tags": current_tags
        }
    }

    # Send PUT request to update tags
    response = requests.put(subscription_tags_url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Tag '{tag_key}: {tag_value}' was successfully added/updated in subscription {subscription_id}.")
    else:
        print(f"Error adding tag to subscription {subscription_id}:", response.json())

# Calculate deletion date based on the Duration tag
def calculate_deletion_date(duration_value):
    match = re.search(r'(\d+)\s*months?', duration_value, re.IGNORECASE)
    if match:
        months = int(match.group(1))
        deletion_date = datetime.now() + relativedelta(months=months)
        return deletion_date.strftime("%d/%m/%Y")
    return None

# Check if the 'Duration' tag contains a number
def has_valid_duration(tags):
    if "Duration" in tags:
        return re.search(r'\d+', tags["Duration"]) is not None
    return False

# Calculate days until subscription deletion
def days_until_deletion(deletion_date):
    try:
        deletion_datetime = datetime.strptime(deletion_date, "%d/%m/%Y")
        today = datetime.now()
        delta = (deletion_datetime - today).days
        return delta if delta >= 0 else 0  # Return 0 if the date has passed or is today
    except ValueError:
        print(f"Date format error: {deletion_date}")
        return None

# Send an email using Microsoft Graph API
def send_email_with_graph(access_token, recipient_emails, subject, body, sender_email):
    url = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    to_recipients = [{"emailAddress": {"address": email}} for email in recipient_emails]
    email_data = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": to_recipients
        },
        "saveToSentItems": "true"
    }

    response = requests.post(url, headers=headers, json=email_data)
    if response.status_code == 202:
        print(f"Email was sent to {', '.join(recipient_emails)}.")
    else:
        print("Error sending email:", response.json())

def get_email_recipients_from_tags(tags):
    recipients = []
    
    # Retrieve email addresses from the Business Owner tag
    business_owner = tags.get("Business owner", "").strip()
    if business_owner:
        recipients.extend([email.strip() for email in business_owner.split(";") if email.strip()])
    
    # Retrieve email addresses from the Technical Expert tag
    technical_expert = tags.get("Technical Expert", "").strip()
    if technical_expert:
        recipients.extend([email.strip() for email in technical_expert.split(";") if email.strip()])
    
    # Always add default notification email
    recipients.append("<DEFAULT_NOTIFICATION_EMAIL>")
    
    # Remove duplicates (in case the default email was already in the tags)
    recipients = list(set(recipients))
    
    return recipients


# Main logic
access_token = get_access_token(scope="https://management.azure.com/.default")
if access_token:
    print("Fetching subscriptions...\n")
    subscriptions = list_subscriptions(access_token)
    if subscriptions:
        for sub in subscriptions:
            tags = get_subscription_tags(access_token, sub["id"])
            if has_valid_duration(tags):  # Filter subscriptions with a valid Duration tag
                duration = tags.get("Duration", "None")
                technical_expert = tags.get("Technical Expert", "None")
                if "Deletion Date" in tags:
                    deletion_date = tags["Deletion Date"]
                    days_remaining = days_until_deletion(deletion_date)
                    print(f"Subscription: {sub['name']} (ID: {sub['id']})")
                    print(f"  Duration: {duration}")
                    print(f"  Technical Expert: {technical_expert}")
                    print(f"  Deletion Date: {deletion_date}")
                    print(f"  Days remaining until deletion: {days_remaining}")
                    if days_remaining == 14 and tags.get("Notification Sent", "False") != "True":
                        # Send email
                        # Add Business Owner if exists
                        email_subject = f"Notification: Subscription {sub['name']} will expire in 14 days"
                        email_body = f"""
                        Dear Team,

                        This is a reminder that the Azure subscription {sub['name']} (ID: {sub['id']}) is set to expire in {days_remaining} days.

                        Subscription Details:
                        - Subscription Name: {sub['name']}
                        - Subscription ID: {sub['id']}
                        - Expiration Date: {deletion_date}
                        """
                        # Add Business Owner if exists
                        business_owner = tags.get("Business owner", "None").strip()
                        if business_owner != "None":
                            email_body += f"- Business Owner: {business_owner}\n"

                        # Add Technical Expert if exists
                        technical_expert = tags.get("Technical Expert", "None").strip()
                        if technical_expert != "None":
                            email_body += f"- Technical Expert: {technical_expert}\n"

                        email_body += f"""
                        Action Required:
                        If this subscription is still required, please create a ticket in Jira Service Desk to request an extension before the expiration date.
                        You can create the ticket here: <JIRA_TICKET_URL>

                        If no action is taken, the subscription will be automatically canceled on the expiration date.
                        If you have any questions or need assistance, please contact the Cloud team.

                        Best regards,  
                       YOUR_TEAM_NAME
                        """

                        # Retrieve email addresses from Business Owner and Technical Expert tags
                        recipient_emails = get_email_recipients_from_tags(tags)
                        
                        # Send email
                        graph_token = get_access_token(scope="https://graph.microsoft.com/.default")
                        if graph_token:
                            send_email_with_graph(graph_token, recipient_emails, email_subject, email_body, "<SENDER_EMAIL>")
                            add_or_update_subscription_tag(access_token, sub["id"], "Notification Sent", "True")
                    elif days_remaining == 0:  # Cancel subscription when Deletion Date equals 0
                        print(f"Creating ticket and sending email for subscription {sub['name']} (ID: {sub['id']})...")
                        # Retrieve email addresses from Business Owner and Technical Expert tags
                        recipient_emails = get_email_recipients_from_tags(tags)
                        # Add ticket email to recipient list
                        #recipient_emails.append("<TICKET_EMAIL>")
                                            
                        print("-" * 40)          
                        # Send email after subscription cancellation
                        email_subject = f"Notification: Subscription {sub['name']} has been canceled"
                        email_body = f"""
                        Dear Team,

                        The Azure subscription {sub['name']} (ID: {sub['id']}) has been canceled as of {datetime.now().strftime("%d/%m/%Y")}.

                        Subscription Details:
                        - Subscription Name: {sub['name']}
                        - Subscription ID: {sub['id']}
                        """
                        # Add Business Owner if exists
                        business_owner = tags.get("Business owner", "None").strip()
                        if business_owner != "None":
                            email_body += f"- Business Owner: {business_owner}\n"

                        # Add Technical Expert if exists
                        technical_expert = tags.get("Technical Expert", "None").strip()
                        if technical_expert != "None":
                            email_body += f"- Technical Expert: {technical_expert}\n"

                        email_body += f"""
                        Additional Information:
                        The subscription was canceled as part of the automated cleanup process. If this subscription is still required, please create a ticket in Jira Service Desk to request its reactivation:
                         <JIRA_TICKET_URL>

                        Please note: Reactivation of the subscription is possible within 90 days from the date of this email. After this period, the subscription and its associated resources will be permanently deleted.
                        If you have any questions or need assistance, please contact the Cloud team.

                        Best regards,  
                        YOUR_TEAM_NAME
                        """
                        graph_token = get_access_token(scope="https://graph.microsoft.com/.default")
                        if graph_token:
                            send_email_with_graph(graph_token, recipient_emails, email_subject, email_body, "<SENDER_EMAIL>")
                else:
                    deletion_date = calculate_deletion_date(duration)
                    if deletion_date:
                        print(f"Subscription: {sub['name']} (ID: {sub['id']})")
                        print(f"  Duration: {duration}")
                        print(f"  Technical Expert: {technical_expert}")
                        print(f"  Calculated Deletion Date: {deletion_date}")
                        
                        # Add the Deletion Date tag
                        add_or_update_subscription_tag(access_token, sub["id"], "Deletion Date", deletion_date)
                print("-" * 40)
    else:
        print("No subscriptions to display.")
else:
    print("Authentication failed.")
