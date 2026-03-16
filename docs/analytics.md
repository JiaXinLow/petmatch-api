# 📊 Analytics Models
This document describes the logic behind the two heuristic scoring systems:
- **Return-Risk Score (post-adoption)**
- **Welfare / Stress Score (in-shelter)**
Both are transparent, explainable, rule-based models designed for realism and teachability.

---
# 1.0 Return-Risk Model  
Estimates the likelihood that a pet may be **returned after adoption**.

Uses signals supported by shelter-welfare literature and public adoption reports.

## 1.1 Factor used
| Factor | Description |
|--------|-------------|
| Age | seniors & very young animals have different risk patterns |
| Species | cats vs dogs vs other animals |
| Breed group | mixed-breed uncertainty penalty |
| Documentation quality | unknown sex, missing fields |
| Coat visibility | dark coat penalty (adoption likelihood effect) |
| Cohort adoption rate | lower cohort success increases risk |

## 1.2 Endpoint
```bash
GET /api/analytics/return-risk/{pet_id}
GET /api/analytics/return-risk/by-external-id/{external_id}
```

## 1.3 Example Response
```json
{
  "pet_id": 118,
  "risk_score": 68,
  "components": [
    {"name": "species_other_penalty", "weight": 12},
    {"name": "unknown_sex_penalty", "weight": 8},
    {"name": "dark_coat_penalty", "weight": 5},
    {"name": "mixed_breed_unclassified_penalty", "weight": 4}
  ],
  "explanation": "Heuristic risk score for potential post-adoption returns."
}
```
---
# 2.0 Welfare/ Stress Model
Estimates the current level of stress or welfare concerns for a pet inside a shelter.

Factors chosen reflect handling practices and enrichment guidelines from real shelters.

# 2.1 Factors Used
| Factor               | Description                                           |
|----------------------|-------------------------------------------------------|
| Breed group          | e.g. herding breeds → high stimulation needs         |
| Age                  | puppies/seniors need more support                    |
| Species enrichment   | cats vs dogs differ in social needs                  |
| Documentation quality| missing sex info adds uncertainty                    |
| Coat visibility      | minor impact on behavior assessment                  |

# 2.2 Endpoint
```bash
GET /api/analytics/welfare/{pet_id}
GET /api/analytics/welfare/by-external-id/{external_id}
```

# 2.3 Example Response
```json
{
  "pet_id": 201,
  "welfare_score": 62,
  "components": [
    {"name": "herding_group_weight", "weight": 12},
    {"name": "senior_age_penalty", "weight": 10}
  ],
  "advisory": [
    "Increase enrichment activities.",
    "Provide additional comfort for senior animals."
  ]
}
```
---
# 3.0 Why Heuristic Models?
✔ Transparent: Examiners can easily inspect logic during Q&A.
✔ Explainable: Scores break down into weighted components.
✔ Realistic-lite: Reflects real-world decision factors without needing ML/NLP.
✔ Testable: Unit & integration tests validate each component independently.

---
# 4.0 Technical Notes
- All analytics logic lives in:
    - services/return_risk.py
    - services/welfare.py
- Analytics routers enforce optional API-key protection
- Internal helpers use consistent patterns:
    - score += weight
    - components.append({ name, weight })
- Outputs follow a consistent Pydantic schema

---
# 5.0 Summary
The analytics system provides:
- Clear and interpretable scores
- Useful operational insights
- A good balance of realism and coursework scoping
- Fully documented behavior for testing and assessment
It demonstrates architectural clarity, domain reasoning, and real-world relevance.