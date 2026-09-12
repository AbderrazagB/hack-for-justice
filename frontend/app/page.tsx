"use client";

import { type FormEvent, useState } from "react";

import { submitQuery } from "@/lib/api";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await submitQuery(question);
      setAnswer(response.answer);
    } catch (requestError) {
      setAnswer("");
      setError(
        requestError instanceof Error ? requestError.message : "Request failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-24 text-slate-900">
      <section className="mx-auto max-w-2xl rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">
          Sahilli · سهّلي
        </p>
        <h1 className="mt-3 text-3xl font-bold">Ask the prototype</h1>
        <p className="mt-3 text-slate-600">
          This form calls the FastAPI query endpoint and displays its response.
        </p>

        <form className="mt-8 flex gap-3" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="question">
            Question
          </label>
          <input
            id="question"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question…"
            required
          />
          <button
            className="rounded-lg bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={loading}
          >
            {loading ? "Asking…" : "Ask"}
          </button>
        </form>

        {answer && (
          <div className="mt-6 rounded-lg bg-emerald-50 p-4 text-emerald-900">
            {answer}
          </div>
        )}
        {error && (
          <div className="mt-6 rounded-lg bg-red-50 p-4 text-red-800">
            {error}
          </div>
        )}
      </section>
    </main>
  );
}
