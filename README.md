# Oilcast public CPU model service

Deployment prepared for the independent repository `lins58308/oilcast-models`. Not yet created or deployed. Only public CPC oil prices, crude/FX observations, news metadata and learned model parameters are included. No Android billing/carrier data, Play signing keys or user credentials are uploaded.

The six Java model classes match Android3.3.5. `run_training.py` compiles with JDK17 and downloads the pinned/checksummed org.json dependency. `pipeline.py` runs in GitHub Actions with the workflow token and an independent RSA model-signing Secret; it restores public training history, reports progress, trains, validates against the App's pinned public key, uploads immutable model/envelope assets as a draft, reads them back to verify hashes, then publishes the latest release. It persists a checkpoint; recovery also uses the latest public model if a checkpoint save failed. It never silently resets on a 403/network failure or overwrites an existing model release.

## Activation after account operations are available

1. Create the independent public repository above; do not change the existing BreezeFlow/Unbound projects.
2. Upload this source tree, excluding private/, build/, output/, caches and logs. The workflow is included and third-party actions are pinned to commits verified on 2026-10-12. `model-public.txt` is safe to publish and must equal the App's cloud-model-public.pem.
3. Store the independently generated model private key only as `MODEL_SIGNING_KEY_B64` in repository Actions Secrets. It is the Base64 of the PKCS8 PEM, not the Play key. No private key is included in this deliverable.
4. Run the workflow manually first. Verify the real CPC/source fetches, signed model publication, immutable model URL, checkpoint persistence, status and a second run advancing the server revision. Only then set `OILCAST_SERVICE_ENABLED=true` to enable the six-hour cron. Exact start times are not guaranteed.
5. App3.3.5 already contains the loader, verifier, merger and UI, but its `cloud-model-config.json` ready flag remains false. Enable it and rebuild only after a live download and signature/schema/current-CPC verification. Real Android background, restarts and notifications still need device validation.

The model download entry is releases/latest/download/envelope.json. The signed manifest points to that release's immutable model.json. App users do not need a GitHub account/token. Job progress is published as status.json on the repository's default branch; do not rename the default branch from main without updating the App status URL.

Public standard GitHub-hosted runners are the intended deployment; no Azure resources, private paid runner or subscriptions are created. Set repository protections and inspect Actions settings. Training checkpoints and model assets contain public metadata; the service does not publish full news articles. Historical/demo output is rejected by the production validator/publisher.

## Local checks completed

Forty server model/contract assertions pass on historical data. Twelve publisher test cases use a fake API and do not send any requests. App tests separately cover download redirects/size/cancellation, signature/data/parameter consistency, first-forecast preservation, newer/corrected CPC precedence, history merging, rollback and replay, plus UI progress and local fallback. These are not claims of live deployment or Android runtime verification.
