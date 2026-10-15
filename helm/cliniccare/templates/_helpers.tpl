{{- define "cliniccare.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Release name alone when it already contains the chart name (cliniccare -> cliniccare-backend). */}}
{{- define "cliniccare.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else if contains (include "cliniccare.name" .) .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "cliniccare.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "cliniccare.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
app.kubernetes.io/name: {{ include "cliniccare.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | trunc 63 | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: cliniccare
{{- end -}}

{{/* Common labels plus the component. Usage: include "cliniccare.componentLabels" (dict "ctx" . "component" "backend") */}}
{{- define "cliniccare.componentLabels" -}}
{{ include "cliniccare.labels" .ctx }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Usage: include "cliniccare.selectorLabels" (dict "ctx" . "component" "backend") */}}
{{- define "cliniccare.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cliniccare.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "cliniccare.image" -}}
{{- $tag := required "image.tag is required (the pipeline passes the commit SHA)" .ctx.Values.image.tag -}}
{{- printf "%s/cliniccare-%s:%s" .ctx.Values.image.registry .component $tag -}}
{{- end -}}

{{- define "cliniccare.secretName" -}}
{{- printf "%s-db" (include "cliniccare.fullname" .) -}}
{{- end -}}

{{/* Restricted pod security: non-root, no privilege escalation, no capabilities. */}}
{{- define "cliniccare.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}

{{- define "cliniccare.podSecurityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}
