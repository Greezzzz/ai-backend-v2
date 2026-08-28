from pydantic import BaseModel


class OtelSettings(BaseModel):
    enabled: bool = False
    exporter_otlp_endpoint: str = "http://localhost:4318"
    service_name: str = "ai-backend-v2"
