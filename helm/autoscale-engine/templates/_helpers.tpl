{{/*
Common labels applied to all resources.
*/}}
{{- define "autoscale-engine.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: autoscale-engine
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Component-specific labels.
Usage: {{ include "autoscale-engine.componentLabels" (dict "component" "api-server" "root" .) }}
*/}}
{{- define "autoscale-engine.componentLabels" -}}
app: {{ .component }}
{{ include "autoscale-engine.labels" .root }}
{{- end }}
