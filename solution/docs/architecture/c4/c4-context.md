# C4 Level 1: System Context

> Who uses HealthStream RAG and what external systems does it interact with?

```mermaid
C4Context
    title HealthStream RAG - System Context

    Person(patient, "Patient", "Health app user on iPhone/Android with CPAP device")
    Person(clinician, "Clinician", "Care provider using patient management portal")

    System(healthstream, "HealthStream RAG", "HIPAA-compliant AI chatbot answering questions from personal health data")

    System_Ext(healthkit, "Apple HealthKit / Google Health Connect", "Wearable and phone health data - sleep, activity, vitals")
    System_Ext(ehr_systems, "EHR Systems", "Electronic Health Records - HL7v2, CCDA formats")
    System_Ext(fhir_sources, "FHIR R4 Sources", "External clinical data providers and health information exchanges")

    Rel(patient, healthstream, "Asks therapy questions via app", "HTTPS/WSS")
    Rel(clinician, healthstream, "Queries patient population data", "HTTPS")
    Rel(healthstream, healthkit, "Ingests real-time health events", "Kinesis + API")
    Rel(healthstream, ehr_systems, "Batch ingests clinical records", "SFTP/S3")
    Rel(healthstream, fhir_sources, "Receives FHIR R4 resources", "REST FHIR API")
```

## Key Decisions

- **Patients** interact via a mobile health app (e.g. companion CPAP app)
- **Clinicians** access via a patient management portal
- **Three data source types** each with a dedicated ingestion pipeline
- All interactions go through HIPAA controls (encryption, audit, patient isolation)
