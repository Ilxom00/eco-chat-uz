async def generate_general_stats_excel(data: list[dict]) -> bytes:
    return b""

async def generate_topic_stats_excel(topic_name: str, data: list[dict]) -> bytes:
    return b""

async def generate_employee_detail_excel(employee_data: dict) -> bytes:
    return b""

async def parse_import_excel(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    return [], []

async def generate_import_template() -> bytes:
    return b""
