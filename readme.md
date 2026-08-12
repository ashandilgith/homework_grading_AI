# 🎓 Eskwela AI | Automated Grading Pipeline

[Streamlit App](https://eskwela2.streamlit.app/)


**Eskwela AI** is an end-to-end machine learning application that automates the grading of handwritten or digital student exams. Powered by Google's Gemini Vision models, it compares student submissions against a strict marking scheme, calculates scores, and generates aesthetic, actionable PDF feedback reports in seconds.

Built by Ashan Bandaranayeke

---

##  Business Value
For educational institutions and tutors, grading is the most time-consuming bottleneck. Eskwela AI solves this by:
* **Reducing Grading Time by 95%:** Batch-processes multiple multi-page PDFs simultaneously.
* **Cost-Optimized Architecture:** Leverages the `gemini-3.5-flash` model for high-speed, ultra-low-cost token processing (fraction of a penny per paper) without sacrificing reasoning quality.
* **Zero-Retention Privacy:** Deployed statelessly. Student papers are processed in ephemeral server memory and instantly wiped after the report is generated, ensuring strict data privacy.

---

##  Technical Architecture & Stack

* **Frontend:** Streamlit (with custom CSS injected to override default webkit rendering for seamless dark-mode UI).
* **LLM Engine:** Google Generative AI (`gemini-3.5-flash`) via strict JSON-enforced zero-shot prompt engineering.
* **Document Processing:** Native Gemini Multimodal Vision (PDF ingestion).
* **Report Generation:** `fpdf` for dynamic, programmatic PDF creation.
* **Data & Storage (Optional Cloud Mode):** PostgreSQL for log tracking and Google Cloud Storage for persistent document hosting.

###  Engineering Highlights
* **Graceful Degradation:** The application features built-in exception handling for cloud infrastructure. If the PostgreSQL database or Google Cloud Storage buckets are offline or unreachable, the app seamlessly falls back to a 100% local/stateless processing mode without crashing the UI.
* **Token Quota Management:** Includes a lightweight, `.env`-driven role-based access control (RBAC) system to manage tutor token limits and prevent API abuse.
* **JSON Parsing Safety:** Uses regex cleaning to strip markdown artifacts (````json`) from LLM outputs before parsing, ensuring pipeline stability even when the model hallucinates formatting.

---

## ⚙️ How It Works (The Pipeline)

1. **Upload Phase:** User uploads a Marking Scheme (PDF) and $N$ Student Submissions (PDFs).
2. **Context Window Assembly:** The files are pushed to Gemini's ephemeral file API alongside a strict, rule-based system prompt instructing the model to act as a rigorous Teaching Assistant.
3. **Inference & Extraction:** The model grades each sub-question independently, provides actionable feedback, and outputs the results in a strict, pre-defined JSON schema.
4. **Validation:** A Python logic layer intercepts the JSON, verifies the math (checking actual scores against maximum denominators), and formats the text.
5. **Report Generation:** `fpdf` compiles the verified data into a branded, easy-to-read PDF and surfaces it to the user.

---
