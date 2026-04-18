import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  text?: string;
}

export default function LoadingSpinner({
  text = "Analysing...",
}: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-12">
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
      <p className="text-sm text-gray-500 font-medium">{text}</p>
    </div>
  );
}
