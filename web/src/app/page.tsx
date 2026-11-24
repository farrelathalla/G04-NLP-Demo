import { Demo } from "@/components/demo/demo";
import { ModelsSection } from "@/components/demo/models-section";
import { SiteHeader } from "@/components/demo/site-header";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 pb-24">
        <section className="pt-16 pb-12">
          <p className="text-sm font-medium text-accent-brand">Group G04 · NLP Final Project</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-balance">
            From a court decision PDF to crime type, case facts, and sentence
          </h1>
          <p className="mt-4 max-w-2xl text-base text-muted-foreground">
            Upload one Indonesian criminal judgment. The pipeline reads the PDF, classifies the crime, extracts the
            sentencing factors, and predicts the prison sentence in months.
          </p>
          <ol className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              ["1", "Crime classification", "TF-IDF word and character features with a linear SVM"],
              ["2", "Information extraction", "Rules and an IndoBERT tagger fill 14 factor slots"],
              ["3", "Sentence prediction", "LightGBM on the case facts, plus the champion blend"],
            ].map(([n, title, text]) => (
              <li key={n} className="flex gap-3 rounded-xl border bg-card p-4">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-xs">
                  {n}
                </span>
                <div>
                  <p className="text-sm font-medium">{title}</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
        <Demo />
        <ModelsSection />
      </main>
      <footer className="border-t py-6 text-center text-xs text-muted-foreground">
        Course experiment for NLP. The output is not legal advice.
      </footer>
    </>
  );
}
