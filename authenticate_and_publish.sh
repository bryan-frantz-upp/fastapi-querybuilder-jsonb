poetry config http-basic.nex oauth2accesstoken "$(gcloud auth print-access-token)"
poetry publish --build --repository nex