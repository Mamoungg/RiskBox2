export type TaskType =
  | "code_change"
  | "payment"
  | "code_and_payment"
  | "ops"
  | "custom";

export type Verdict = "SAFE" | "NEEDS_APPROVAL" | "BLOCKED";

export type PaymentRequest = {
  amount: number;
  currency: string;
  recipient: string;
  invoice_reference?: string | null;
};

export type Constraints = {
  max_risk_score: number;
  require_citations: boolean;
};

export type EvaluateRequest = {
  task_type: TaskType;
  action_summary: string;
  repository_url?: string | null;
  repository_ref?: string | null;
  diff_text?: string | null;
  policy_urls?: string[];
  documentation_urls?: string[];
  payment_request?: PaymentRequest | null;
  constraints?: Constraints;
};

export type EvaluateResponse = {
  run_id: string;
  status: Verdict;
  risk_score: number;
  summary: string;
  reasons: string[];
  safer_alternative: string;
  context_assessment: Record<string, unknown>;
  code_assessment: Record<string, unknown>;
  payment_assessment: Record<string, unknown>;
  llm_synthesis: Record<string, unknown>;
  timings: Record<string, number | string>;
};
