# Hackathon-ESSEC-Eika

Team members : Emma LEGRAND (EMLV), Antoine VANSIELEGHEM (ESILV), Kylie WU (ESILV), Ilan ZINI (ESILV)

Track : Industry

Today, most insurance contracts evolve on fixed dates, with little consideration for the actual life events of the customer.
Our solution (B2B) introduces an intelligent AI system that detects key life moments, such as moving to a new home, having a child, or switching to remote work, and automatically triggers a targeted review of the customer’s insurance contract.
The result : the customer is better protected, right when it matters.
The insurer strengthens loyalty while increasing the relevance and timing of new offers.

### Today's market situation
...

### Database
We use a customer database from Kaggle (https://www.kaggle.com/datasets/stealthtechnologies/regression-dataset-for-household-income-analysis). We complete it by filling it with more columns and fictional life events (e.g. buying a home, having a child, changing jobs). Based on these events, the system generates personalized insurance recommendations, such as : "Your client X just purchased a home — consider offering them a tailored home insurance plan." 

To see the detail of each column : see the PDF document named "Explanations about each columns of the clients dataset".

We then added the dataset in AWS S3 and Redshift.
...

### Agents
Connected via Amazon Bedrock (Claude 3.5, Titan...), orchestrated with Python.

+ PDF document named "The different types of insurance contracts and details".

...

We chose Amazon Titan Text Express for its balance of performance, reliability, and enterprise-grade data privacy. As part of AWS Bedrock, Titan ensures that all data processing complies with strict security and confidentiality standards, with no model training on customer data, and all inference happening in a controlled, fully managed environment. This makes it ideal for handling sensitive insurance-related information while delivering high-quality language understanding and generation.

### Backend & frontend
We are building a fully interactive web application using Streamlit, designed for two distinct user roles (Client or Advisor). Users log in via a clean dual-role interface.
- Clients : Can log in, view their profile (pulled from the database), and edit selected attributes/simulate real-life changes, save the changes.
- Advisors : Can log in, see all clients and recent updates, get notified of changes, and trigger an AI assistant to get contextual insurance recommendations.

We use Streamlit’s native hot-reload feature so the app updates instantly with every change.

...

### Business model
A charged feature that is suggested to the client...
...

### About confidentiality
...



###

