import Link from "next/link";

export default function ResultsPage() {
  return (
    <main className="app-shell">
      <section className="result-card empty-state">
        <div className="empty-state-inner">
          <div className="radar-mark">TX</div>
          <h2>Results now live on the main console.</h2>
          <p>
            The current frontend keeps input and decision output together so a lender can adjust the file
            and review the updated credit view without switching pages.
          </p>
          <Link className="submit-button" href="/" style={{ display: "inline-block", textDecoration: "none" }}>
            Open valuation console
          </Link>
        </div>
      </section>
    </main>
  );
}
