#!/bin/sh
set -eu

until curl -s -u "elastic:${ELASTIC_PASSWORD}" http://elasticsearch:9200 >/dev/null; do
  sleep 5
done

until curl -s http://kibana:5601/api/status >/dev/null; do
  sleep 5
done

curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X PUT http://elasticsearch:9200/_ingest/pipeline/shopping-platform-logs-pipeline \
  --data-binary @/assets/ingest-pipeline.json >/dev/null

curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X PUT http://elasticsearch:9200/_index_template/shopping-platform-logs-template \
  --data-binary @/assets/index-template.json >/dev/null

curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -X POST http://kibana:5601/api/data_views/data_view \
  -d '{"data_view":{"name":"shopping-platform-logs","title":"shopping-platform-logs-*","timeFieldName":"@timestamp"}}' >/dev/null || true
