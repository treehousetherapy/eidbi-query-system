# EIDBI Query System - GCP Deployment Permissions

## Current Permission Issues

When trying to deploy the EIDBI Query System to Google Cloud Run, we are encountering the following permission error:

```
ERROR: (gcloud.builds.submit) INVALID_ARGUMENT: could not resolve source: googleapi: Error 403: 25849992695-compute@developer.gserviceaccount.com does not have storage.objects.get access to the Google Cloud Storage object. Permission 'storage.objects.get' denied on resource (or it may not exist).
```

This indicates that the compute service account used for Cloud Build and Cloud Run deployments lacks the necessary permissions to access Cloud Storage objects.

## Required Permissions

The following service accounts need specific permissions:

1. **Compute Service Account** (`25849992695-compute@developer.gserviceaccount.com`):
   - Needs `roles/storage.objectAdmin` or `roles/storage.objectViewer` role for the project's Cloud Storage buckets
   - This is required for Cloud Build to access deployment artifacts

2. **Cloud Build Service Account** (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`):
   - Needs `roles/run.admin` to deploy to Cloud Run
   - Needs `roles/iam.serviceAccountUser` to use service accounts
   - Needs `roles/storage.admin` to access storage buckets

3. **EIDBI Service Account** (`eidbi-service-account@[PROJECT_ID].iam.gserviceaccount.com`):
   - Already created and properly configured with necessary permissions

## Required Changes by GCP Administrator

1. Grant Storage Object Admin role to the compute service account:
```bash
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member="serviceAccount:25849992695-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

2. Grant direct bucket access to the compute service account:
```bash
gcloud storage buckets add-iam-policy-binding gs://[PROJECT_ID]_cloudbuild \
    --member="serviceAccount:25849992695-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

3. If there's an organization policy that prevents public access to Cloud Run services, either:
   - Request an exemption for this specific service, or
   - Keep it as an authenticated service (current configuration)

## Once Permissions Are Resolved

Once these permissions are granted, deployment can be triggered by:

1. Pushing to the GitHub repository (if Cloud Build triggers are set up)
2. Running the following command:
```bash
gcloud builds submit --config=cloudbuild.yaml
```

## Local Development (Already Working)

While waiting for permission issues to be resolved, development can continue locally using:
- `start_backend.bat` - Runs the backend service on http://localhost:8000
- `start_frontend.bat` - Runs the frontend Streamlit app on http://localhost:8501 