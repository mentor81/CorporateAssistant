import json

from app.schemas.candidate import CandidateData


def candidate_to_json_string(candidate_data: CandidateData) -> str:
    data_dict = candidate_data.model_dump()

    return json.dumps(
        data_dict,
        ensure_ascii=False,
        indent=2
    )
