"use client";

interface ModelVersion {
  id: string;
  provider_name: string;
  model_name: string;
  alias_name: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

interface Props {
  model: ModelVersion;
}

export function ModelVersionDetail({ model }: Props) {
  return (
    <div className="border rounded-lg p-5 space-y-2">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">{model.model_name}</h2>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            model.is_active
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-400"
          }`}
        >
          {model.is_active ? "Active" : "Inactive"}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
        <dt className="text-muted-foreground">ID</dt>
        <dd className="font-mono text-xs truncate">{model.id}</dd>

        <dt className="text-muted-foreground">Provider</dt>
        <dd>{model.provider_name}</dd>

        {model.alias_name && (
          <>
            <dt className="text-muted-foreground">Alias</dt>
            <dd>{model.alias_name}</dd>
          </>
        )}

        <dt className="text-muted-foreground">Registered</dt>
        <dd>{model.created_at.slice(0, 19).replace("T", " ")} UTC</dd>

        {model.notes && (
          <>
            <dt className="text-muted-foreground">Notes</dt>
            <dd className="italic">{model.notes}</dd>
          </>
        )}
      </dl>
    </div>
  );
}
