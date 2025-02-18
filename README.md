# Azure Subscription Lifecycle Notifier

Azure Subscription Lifecycle Notifier is an automation tool designed to manage Azure subscriptions and notify relevant stakeholders about upcoming subscription expirations. It leverages subscription tags to track and manage the lifecycle of each subscription.

## Key Features

- **Authentication:** Uses a service principal to retrieve access tokens from Azure Active Directory.
- **Subscription Listing:** Fetches a list of Azure subscriptions available to the service principal.
- **Tag Management:** Reads, adds, or updates subscription tags to track lifecycle data.
- **Deletion Date Calculation:** Computes the deletion date based on a `Duration` tag value.
- **Notification:** Sends email notifications via the Microsoft Graph API when:
  - A subscription is approaching expiration (e.g., 14 days remaining).
  - A subscription has reached its cancellation date.
- **Automated Actions:** Flags subscriptions as notified to prevent duplicate emails.

## Tag Details

The tool relies on several subscription tags to control its behavior:

- **Duration:**  
  - **Purpose:** Specifies the lifespan of the subscription.  
  - **Format:** A string that includes a number followed by the word "month" or "months" (e.g., "3 months").  
  - **Usage:** Used to calculate the deletion date by adding the specified number of months to the current date.

- **Deletion Date:**  
  - **Purpose:** Indicates the calculated date on which the subscription should be canceled if no extension is requested.  
  - **Format:** A date in the format `DD/MM/YYYY`.  
  - **Usage:** If this tag is not present, it is calculated from the `Duration` tag and then added to the subscription. The tool also uses this tag to determine the number of days remaining until deletion.

- **Notification Sent:**  
  - **Purpose:** Serves as a flag to indicate whether a notification email has already been sent for an upcoming expiration.  
  - **Format:** A string value (`"True"` or `"False"`).  
  - **Usage:** Prevents the system from sending duplicate notifications when 14 days remain.

- **Business owner:**  
  - **Purpose:** Contains one or more email addresses of the business owner(s) responsible for the subscription.  
  - **Format:** One or more email addresses separated by semicolons (e.g., `owner@example.com; owner2@example.com`).  
  - **Usage:** Email notifications include these addresses as recipients to ensure that the relevant business stakeholders are informed.

- **Technical Expert:**  
  - **Purpose:** Contains one or more email addresses of the technical expert(s) associated with the subscription.  
  - **Format:** One or more email addresses separated by semicolons.  
  - **Usage:** Helps ensure that technical contacts are notified about the subscription’s status.

## Prerequisites

- Python 3.6+
- An Azure service principal with permissions to manage subscriptions.
- Access to Microsoft Graph API for email notifications.
- Python packages (see [requirements.txt](requirements.txt)):
  - `requests`
  - `python-dateutil`

## Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
   cd <YOUR_REPO_NAME>
