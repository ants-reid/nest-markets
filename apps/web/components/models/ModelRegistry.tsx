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
  models: ModelVersion[];
  onSelect?: (model: ModelVersion) => void;
}

export function ModelRegistry({ models, onSelect }: Props) {
  if (models.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">No models registered.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {models.map((m) => (
        <li
          key={m.id}
          className="border rounded p-3 cursor-pointer hover:bg-accent transition-colors"
          onClick={() => onSelect?.(m)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onSelect?.(m)}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm">{m.model_name}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                m.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
              }`}
            >
              {m.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {m.provider_name} · {m.created_at.slice(0, 10)}
          </p>
        </li>
      ))}
    </ul>
  );
}
