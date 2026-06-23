from pathlib import Path


def load_skill():
    skill_path = Path( "SKILL.MD")

    with open(skill_path, "r", encoding="utf-8") as f:
        return f.read()


def support_agent(query):

    skill_content = load_skill()

    query_lower = query.lower()

    if "refund" in query_lower:
        issue = "Refund"
        priority = "High"

        response = (
            "We have registered your refund request. "
            "Our team will process it within 3 business days."
        )

    elif "complaint" in query_lower:
        issue = "Complaint"
        priority = "Medium"

        response = (
            "We apologize for the inconvenience. "
            "Your complaint has been logged and will be reviewed."
        )

    elif "escalate" in query_lower:
        issue = "Escalation"
        priority = "High"

        response = (
            "Your request has been escalated "
            "to a senior support specialist."
        )

    else:
        issue = "Product Question"
        priority = "Low"

        response = (
            "Thank you for contacting us. "
            "We will provide product information shortly."
        )

    return {
        "Issue Type": issue,
        "Priority": priority,
        "Response": response,
    }


query = input("Customer Query: ")
result = support_agent(query)

for k, v in result.items():
    print(f"{k}: {v}")