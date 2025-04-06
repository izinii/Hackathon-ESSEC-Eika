# Hackathon-ESSEC-Eika

Team members : Emma LEGRAND (EMLV), Antoine VANSIELEGHEM (ESILV), Kylie WU (ESILV), Ilan ZINI (ESILV)

Track : Industry

Today, most insurance contracts evolve on fixed dates, with little consideration for the actual life events of the customer.
Our solution (B2B) introduces an intelligent AI system that detects key life moments, such as moving to a new home, having a child, or switching to remote work, and automatically triggers a targeted review of the customer’s insurance contract.
The result : the customer is better protected, right when it matters.
The insurer strengthens loyalty while increasing the relevance and timing of new offers.

### Today's market situation
The AI market in the insurance sector is expanding rapidly, offering significant opportunities for innovative solutions.
According to a KPMG study, the global AI market in insurance could reach $79 billion by 2032, reflecting substantial growth potential. Insurance companies must prepare for this increase in their customer base and be ready to offer solutions that meet their clients' needs.

More and more insurers recognize the benefits of AI in improving operational efficiency and customer experience. Companies like Generali, MAIF, and AXA have already started integrating AI to offer personalized and optimized services.

AI analyzes customer data to provide tailored products, enhancing satisfaction, loyalty, and retention. They can also make process automation with tasks such as claims management and underwriting that can be automated, reducing costs and human errors. AI also helps anticipate customer needs and assess risks more accurately, strengthening insurers' competitiveness.
Despite the advantages, challenges remain, including data quality, ethical concerns, and regulatory compliance. Insurers must address these aspects carefully to ensure successful AI adoption and acceptance from both customers and employees.

By integrating AI, our solution will provide real-time personalized recommendations to sales agents, addressing the growing demand for tailored customer experiences. It aligns perfectly with current trends aimed at enhancing efficiency and personalization in insurance services. Our goal is to empower insurance advisors with more effective and relevant recommendations. By leveraging CRM data, our solution will detect life changes and suggest tailored advice to sales agents when an opportunity arises.

Many competitors focus on automating claims processing or underwriting. Our solution, however, delivers real-time proactive recommendations. It considers real-time changes in customer profiles, such as life events (moving, having a child, or approaching retirement) and generates relevant recommendations for sales agents. The tool seamlessly integrates with existing CRM systems (like Salesforce), ensuring an intuitive and smooth experience for agents without requiring process overhauls. Instead of introducing yet another tool or overwhelming agents with unnecessary information, our solution presents tailored recommendations directly within their CRM. Sales agents can choose to act on these insights and contact the customer or disregard them based on their own assessment.


### Database
We use a customer database from Kaggle (https://www.kaggle.com/datasets/stealthtechnologies/regression-dataset-for-household-income-analysis). We complete it by filling it with more columns and fictional life events (e.g. buying a home, having a child, changing jobs). Based on these events, the system generates personalized insurance recommendations, such as : "Your client X just purchased a home — consider offering them a tailored home insurance plan." 

To see the detail of each column : see the PDF document named "Explanations about each columns of the clients dataset".

We then added the dataset in AWS S3 and Redshift.
...

### Architecture
![Architecture](Architecture.png)

### Agents
Connected via Amazon Bedrock (Claude 3.5, Titan...), orchestrated with Python.

+ PDF document named "The different types of insurance contracts and details".

...

We chose the models : 

### Backend & frontend
The backend : 
- Loads customer data from Redshift
- Calls the AI agents (Profile -> Recommendations -> Message)
- Returns the results : structured profile, personalized recommendations [and final message]
- Connects with the Streamlit frontend, which displays everything to the user or the advisor

We are building a fully interactive web application using Streamlit, designed for two distinct user roles (Client or Advisor). Users log in via a clean dual-role interface.
- Clients : Can log in, view their profile (pulled from the database), and edit selected attributes/simulate real-life changes, save the changes.
- Advisors : Can log in, see all clients and recent updates, get notified of changes, and trigger an AI assistant to get contextual insurance recommendations.

We use Streamlit’s native hot-reload feature so the app updates instantly with every change.
...

### Final schema

Database (S3, Redshift)
   ⇅
AI Agents (via Bedrock with boto3)
   ⇅
Backend Python (orchestration)
   ⇅
Frontend Streamlit (UI)

### Business model
Our AI solution requires an initial investment covering development, CRM integration, cloud infrastructure, and customer support. To ensure sustainability, we adopt a hybrid model combining setup fees, subscriptions, and additional monetization.
Insurers pay a one-time integration fee based on implementation complexity. Each agent using the AI subscribes to a monthly plan, ensuring predictable revenue.

To offset potential lossesfo insurrance company from contract adjustments, we offer a premium option that provides continuous monitoring and personalized recommendations. The AI also enhances cross-selling by suggesting complementary policies, increasing revenue per customer while boosting retention.

This model delivers strong value to insurers while generating a stable, diversified revenue stream, reshaping the insurance experience for all stakeholders.

### About confidentiality
...



###

