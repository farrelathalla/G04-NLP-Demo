export type Sample = {
  id: string;
  title: string;
  crime_type: string;
  court: string | null;
  year: number;
  pages: number;
  pdf: string;
  true_months: number;
};

export type ClassScore = { label: string; margin: number; confidence: number };
export type Term = { term: string; weight: number };

export type Task1Result = {
  label: string;
  confidence: number;
  true_label: string | null;
  split: string | null;
  top: ClassScore[];
  steps: {
    clean: { raw_chars: number; clean_chars: number; removed_lines: string[] };
    closing: { removed_chars: number; preview: string };
    citations: { count: number; example: { before: string; match: string } | null };
    names: { count: number; example: { match: string; left: string; right: string } | null };
    view: { chars: number; words: number; preview: string };
    tfidf: {
      word_features: number;
      char_features: number;
      vocabulary: { word: number; char: number };
      top_words: Term[];
      top_chars: Term[];
    };
    svm: { scores: ClassScore[]; evidence: { term: string; contribution: number }[] };
  };
};

export type SlotValue = string | number | boolean | string[];

export type Task2Result = {
  record: Record<string, SlotValue>;
  crime_type_used: string;
  route: Record<string, "rule" | "bert" | "not_applicable">;
  evidence: Record<string, string[]>;
  stats: { raw_words: number; clean_words: number; verdict_masked: number; pseudonym_replacements: number };
  paragraphs: number;
  sections: { name: string; paragraphs: number; preview: string }[];
  pseudonym_example: string | null;
  bert: { excerpt_chars?: number; windows?: number; spans?: Record<string, string[]>; skipped?: string } | null;
};

export type Task3Result = {
  live: {
    model: string;
    months: number;
    base_months: number;
    drivers: { feature: string; value: string | number | null; effect: number }[];
  };
  regex_demand: { months: number | null; type: string; phrase: string | null };
  features: { feature: string; value: string | number | null }[];
  n_features: number;
  champion: {
    months: number | null;
    true_months: number | null;
    split: string;
    prediction_type: string;
    crime_type_true: string;
  } | null;
};

export type AnalyzeResult = {
  doc_id: string;
  file_name: string;
  extraction: {
    pages: number;
    lines: number;
    chars: number;
    words: number;
    sha256: string;
    match: { source: string | null; exact: boolean | null; original_chars: number | null };
    text: string;
  };
  task1: Task1Result;
  task2: Task2Result;
  task3: Task3Result;
  timings_ms: Record<string, number>;
};

export type ModelsInfo = {
  task1: {
    model: string;
    classes: number;
    train_documents: number;
    features: { word: number; char: number };
    metrics: { val: Record<string, number>; test: Record<string, number> };
  };
  task2: { selector: { bert: string[] }; test_scores: Record<string, number> };
  task3: {
    summary: { champion: string; runner_up: string; test: Record<string, number> };
    blend: { model: string; weight: number }[];
    leaderboard: { experiment: string; block: string; val_mae: number; test_mae: number; test_r2: number }[];
  };
};
