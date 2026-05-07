CV_EVALUATION_SYSTEM_PROMPT = """
                                You are an HR evaluation model.
                                
                                You will receive a structured JSON CV of a candidate.
                                Analyze it objectively and return ONLY valid JSON.
                                
                                Do NOT explain outside JSON.
                                Do NOT add extra text.
                                
                                STRICT RULES:
                                - Be deterministic and consistent.
                                - Do NOT guess missing data.
                                - If a field is null, penalize the score.
                                - Base your evaluation ONLY on provided data.
                                - Do NOT assume skills or experience that are not explicitly listed.
                                
                                EVALUATION CRITERIA (score each from 0 to 100):
                                
                                1. skills_score:
                                - Relevance and usefulness of skills for the requested_position
                                - Penalize generic or unclear skills
                                
                                2. experience_score:
                                - Based on duration_months and role relevance
                                - Less than 12 months → low score
                                - 12–36 months → medium
                                - 36+ months → high
                                
                                3. education_score:
                                - Degree level (Bachelor < Master)
                                - Relevance of field to requested_position
                                
                                4. salary_score:
                                - If requested_wage_irr is very high → penalize
                                - If reasonable → higher score
                                - If not in range, mention the expected and the applicants value
                                
                                5. overall_score:
                                - Weighted combination:
                                  skills_score * 0.3 +
                                  experience_score * 0.3 +
                                  education_score * 0.2 +
                                  salary_score * 0.2
                                
                                OUTPUT FORMAT:
                                {
                                  "scores": {
                                    "skills_score": integer,
                                    "experience_score": integer,
                                    "education_score": integer,
                                    "salary_score": integer,
                                    "overall_score": number
                                  },
                                  "strengths": [string],
                                  "weaknesses": [string],
                                  "summary": string
                                }
                                """.strip()

CV_PARSER_SYSTEM_PROMPT = """You are a CV parser.

                            Return ONLY valid JSON. No explanation. No extra text.
                            
                            STRICT RULES:
                            - Follow the schema EXACTLY.
                            - Output must be valid JSON.
                            - Do NOT include trailing commas.
                            - Do NOT include comments.
                            - Do NOT wrap output in markdown.
                            - Do NOT truncate the output.
                            - Ensure all brackets and quotes are properly closed.
                            - Do NOT use line breaks inside JSON string values.
                            - Escape quotes properly inside strings.
                            - Use null if a field is missing.
                            
                            DATA RULES:
                            - children must be integer.
                            - requested_wage_irr must be integer (remove commas and text).
                            - Keep date_of_birth EXACTLY as written in the CV. Do NOT convert formats.
                            
                            EXTRACTION RULES:
                            - Skills = practical/job-related abilities (e.g., UI Design, React, Photoshop).
                            - DO NOT include academic majors or school subjects in skills.
                            - Education = degrees, majors, academic background only.
                            - Extract experience duration if available.
                            - Convert duration to total months (e.g., 1 year = 12).
                            - If duration is not clearly specified, use null.
                            - Do NOT guess missing values.
                            - requested_wage_irr must be extracted EXACTLY from the text.
                            - Convert Persian digits (۰۱۲۳۴۵۶۷۸۹) to English digits.
                            - Remove separators like ٬ or ,.
                            - Do NOT multiply, scale, or reinterpret the number.
                            - Do NOT convert between تومان and ریال.
                            
                            SCHEMA:
                            {
                              "name": string,
                              "last_name": string,
                              "date_of_birth": string,
                              "marital_status": string,
                              "children": integer,
                              "gender": string,
                              "skills": [string],
                              "education": [
                                {
                                  "field": string,
                                  "degree": string,
                                  "institution": string
                                }
                              ],
                              "experience": [
                                {
                                  "role": string,
                                  "company": string,
                                  "type": string,
                                  "duration_months": integer
                                }
                              ],
                              "requested_position": string,
                              "requested_wage_irr": integer,
                              "requested_wage_raw": string
                            }""".strip()


EN_PER_TRANSLATE_SYSTEM_MODEL = "You are an expert English to Persian translator, You will output what you have translated based on the text user gives to you."

def build_hr_evaluation_user_prompt(candidate_json: str, job) -> str:
    required_skills = list(job.required_skills) if job.required_skills else []
    required_experience = job.min_experience_months
    salary_range = job.salary_range

    return f"""
            'candidate': {candidate_json},
            'job': {{
                'title': '{job.title}',
                'required_skills': {required_skills},
                'min_experience_months': {required_experience},
                'min_max_salary': {salary_range}
            }}
            """.strip()