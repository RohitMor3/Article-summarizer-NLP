import tkinter as tk
from tkinter import scrolledtext, ttk
import nltk
from textblob import TextBlob
from newspaper import Article
from collections import Counter
import re
from nltk.tokenize import sent_tokenize

# NLTK setup
for resource in ['punkt', 'punkt_tab', 'stopwords']:
    try:
        nltk.data.find(f'tokenizers/{resource}' if resource.startswith('punkt') else f'corpora/{resource}')
    except:
        nltk.download(resource)

from nltk.corpus import stopwords as nltk_stopwords

STOPWORDS = set(nltk_stopwords.words('english'))

#https://www.moneycontrol.com/news/business/markets/higher-net-worth-for-brokers-funding-via-ncds-for-mtf-and-more-sebi-planning-overhaul-of-leverage-trading-rule-book-13893903.html

#https://www.moneycontrol.com/news/business/information-technology/wipro-to-stay-away-from-campus-hiring-for-now-amid-ai-shift-13890838.html



def copy_to_clipboard(text_widget=None, stringvar=None):
    root.clipboard_clear()
    if text_widget:
        content = text_widget.get(1.0, tk.END).strip()
    elif stringvar:
        content = stringvar.get().strip()
    else:
        return
    root.clipboard_append(content)
    root.update()


def make_copy_btn(parent, text_widget=None, stringvar=None):
    def flash_and_copy():
        copy_to_clipboard(text_widget, stringvar)
        btn.config(text="✔ Copied!")
        root.after(1500, lambda: btn.config(text="⧉ Copy"))

    btn = tk.Button(parent, text="⧉ Copy",
                    command=flash_and_copy,
                    bg="#1e293b", fg="#7dd3fc",
                    font=("Segoe UI", 8), bd=0,
                    cursor="hand2", padx=6, pady=2)
    return btn


#calc reading time
def reading_time(text):
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return words, minutes


#extracting tags
def extract_tags(text, n=8):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    freq = Counter(filtered)
    # Capitalise for display
    return [w.capitalize() for w, _ in freq.most_common(n)]


#bullet summary
def build_short_summary(text, summary_text, n=3):
    sents = sent_tokenize(text)
    words = re.findall(r'\b\w+\b', text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS and len(w) > 3)

    scored = {}
    for s in sents:
        for w in re.findall(r'\b\w+\b', s.lower()):
            if w in freq:
                scored[s] = scored.get(s, 0) + freq[w]

    ranked = sorted(scored, key=scored.get, reverse=True)

    # Prefer sentences that also appear / overlap with article.summary
    summary_words = set(re.findall(r'\b\w+\b', summary_text.lower()))
    boosted = sorted(
        ranked[:20],
        key=lambda s: sum(1 for w in re.findall(r'\b\w+\b', s.lower()) if w in summary_words),
        reverse=True
    )

    picked = []
    for s in boosted:
        s = s.strip()
        if len(s) > 40 and s not in picked:
            picked.append(s)
        if len(picked) == n:
            break
    return picked


#analyse button
def analyze():
    url = url_entry.get().strip()
    if not url.startswith("http"):
        status_var.set("❌  Invalid URL — must start with http/https")
        return
    status_var.set("⟳  Loading article…")
    progress.start()
    analyze_btn.config(state="disabled")
    root.after(100, lambda: process(url))


def process(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()

        #author & title
        title_var.set(article.title)
        author_var.set(", ".join(article.authors) if article.authors else "N/A")

        #stats
        word_count, mins = reading_time(article.text)
        stats_var.set(f"📄  {word_count:,} words  •  ⏱  ~{mins} min read")

        #short summary
        short_sents = build_short_summary(article.text, article.summary, n=3)
        short_box.config(state="normal")
        short_box.delete(1.0, tk.END)
        for s in short_sents:
            short_box.insert(tk.END, f"▸  {s}\n\n")
        short_box.config(state="disabled")

        #full summary
        summary_box.config(state="normal")
        summary_box.delete(1.0, tk.END)
        sentences = [s.strip() for s in article.summary.split(". ") if s.strip()]
        for s in sentences:
            summary_box.insert(tk.END, f"•  {s}.\n\n")
        summary_box.config(state="disabled")

        #key insight
        sentences_full = sent_tokenize(article.text)
        word_freq = Counter(
            w for w in re.findall(r'\w+', article.text.lower())
            if w not in STOPWORDS
        )
        sentence_scores = {}
        for sent in sentences_full:
            for word in re.findall(r'\w+', sent.lower()):
                if word in word_freq:
                    sentence_scores[sent] = sentence_scores.get(sent, 0) + word_freq[word]

        ranked_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)
        summary_sentences = set(sent_tokenize(article.summary))

        final_insights = []
        for sent in ranked_sentences:
            if sent not in summary_sentences:
                final_insights.append(sent)
            if len(final_insights) == 4:
                break

        def clean_sentence(s):
            s = s.strip()
            if len(s) > 130:
                s = s[:130].rsplit(" ", 1)[0] + "…"
            return s

        key_box.config(state="normal")
        key_box.delete(1.0, tk.END)
        for i, sent in enumerate(final_insights, start=1):
            key_box.insert(tk.END, f"{i}.  {clean_sentence(sent)}\n\n")
        key_box.config(state="disabled")

        #keyword tags
        tags = extract_tags(article.text, n=10)
        for widget in tags_inner.winfo_children():
            widget.destroy()
        for tag in tags:
            tk.Label(
                tags_inner, text=tag,
                bg="#312e81", fg="#a5b4fc",
                font=("Segoe UI", 9, "bold"),
                padx=8, pady=3, bd=0
            ).pack(side="left", padx=3, pady=4)
        #sentiment
        polarity = TextBlob(article.text).sentiment.polarity
        if polarity > 0.05:
            sentiment, sbg, sfg = "Positive 😊", "#14532d", "#4ade80"
        elif polarity < -0.05:
            sentiment, sbg, sfg = "Negative 😟", "#7f1d1d", "#f87171"
        else:
            sentiment, sbg, sfg = "Neutral 😐", "#78350f", "#facc15"
        sentiment_var.set(sentiment)
        sentiment_label.config(bg=sbg, fg=sfg)

        status_var.set("✔  Done — Article loaded successfully")

    except Exception as e:
        status_var.set(f"❌  Error: {str(e)[:60]}")
    finally:
        progress.stop()
        analyze_btn.config(state="normal")


#window
root = tk.Tk()
root.title("AI Article Summarizer")
root.geometry("1160x780")
root.configure(bg="#0f172a")
root.resizable(True, True)


header = tk.Frame(root, bg="#111827")
header.pack(fill="x")
tk.Label(header, text="AI ARTICLE SUMMARISER",
         font=("Segoe UI", 16, "bold"),
         fg="#7dd3fc", bg="#111827").pack(side="left", pady=15, padx=20)

# Stats shown in header right side
stats_var = tk.StringVar(value="")
tk.Label(header, textvariable=stats_var,
         bg="#111827", fg="#94a3b8",
         font=("Segoe UI", 9)).pack(side="right", padx=20)

#url - input
url_frame = tk.Frame(root, bg="#0f172a")
url_frame.pack(pady=10, fill="x", padx=40)

url_entry = tk.Entry(url_frame, width=80, font=("Segoe UI", 11),
                     bg="#1e293b", fg="white",
                     insertbackground="white", bd=0)
url_entry.pack(side="left", ipady=8, padx=(0, 10))
url_entry.bind("<Return>", lambda e: analyze())

analyze_btn = tk.Button(url_frame, text="ANALYSE →", command=analyze,
                        bg="#7c3aed", fg="white", bd=0,
                        font=("Segoe UI", 10, "bold"), padx=15,
                        cursor="hand2")
analyze_btn.pack(side="left")

#progress bar
status_var = tk.StringVar(value="Paste a URL above and click Analyse")
tk.Label(root, textvariable=status_var,
         bg="#0f172a", fg="#4ade80",
         font=("Segoe UI", 10)).pack(anchor="w", padx=40)

progress = ttk.Progressbar(root, mode="indeterminate")
progress.pack(fill="x", padx=40, pady=4)


tags_outer = tk.Frame(root, bg="#0f172a")
tags_outer.pack(fill="x", padx=40, pady=(0, 4))

tk.Label(tags_outer, text="TOPICS:", fg="#c084fc", bg="#0f172a",
         font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))

tags_inner = tk.Frame(tags_outer, bg="#0f172a")
tags_inner.pack(side="left")


main = tk.Frame(root, bg="#0f172a")
main.pack(fill="both", expand=True, padx=20, pady=6)


title_frame = tk.Frame(main, bg="#1e293b")
title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

title_var = tk.StringVar()
tk.Label(title_frame, textvariable=title_var,
         bg="#1e293b", fg="white",
         font=("Segoe UI", 12, "bold"),
         wraplength=1000, justify="center").pack(padx=10, pady=10)


#short Summary
short_frame = tk.Frame(main, bg="#1e293b")
short_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(0, 6))

short_header = tk.Frame(short_frame, bg="#1e293b")
short_header.pack(fill="x", padx=10, pady=(6, 0))
tk.Label(short_header, text="TL;DR  —  QUICK SUMMARY",
         fg="#34d399", bg="#1e293b",
         font=("Segoe UI", 11, "bold")).pack(side="left")
make_copy_btn(short_header, text_widget=None).pack(side="right")  # placeholder; wired below

short_box = scrolledtext.ScrolledText(short_frame,
                                      font=("Segoe UI", 10),
                                      wrap=tk.WORD,
                                      bg="#0f172a", fg="#d1fae5",
                                      bd=0, height=5)
short_box.pack(fill="both", expand=True, padx=10, pady=6)
short_box.config(state="disabled")

# wire copy btn now that short_box exists
for w in short_header.winfo_children():
    if isinstance(w, tk.Button):
        w.config(command=lambda: (
            root.clipboard_clear(),
            root.clipboard_append(short_box.get(1.0, tk.END).strip()),
            root.update()
        ))


right_top = tk.Frame(main, bg="#0f172a")
right_top.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(0, 6))

sentiment_frame = tk.Frame(right_top, bg="#1e293b")
sentiment_frame.pack(fill="both", expand=True, pady=(0, 6))

tk.Label(sentiment_frame, text="SENTIMENT",
         fg="#c084fc", bg="#1e293b",
         font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 0))

sentiment_var = tk.StringVar(value="Awaiting Input")
sentiment_label = tk.Label(sentiment_frame,
                           textvariable=sentiment_var,
                           font=("Segoe UI", 13, "bold"),
                           width=14, height=2,
                           bg="#1e293b", fg="#cbd5e1")
sentiment_label.pack(pady=10, padx=10, fill="x")

author_frame = tk.Frame(right_top, bg="#1e293b")
author_frame.pack(fill="both", expand=True)

author_hdr = tk.Frame(author_frame, bg="#1e293b")
author_hdr.pack(fill="x", padx=10, pady=(6, 0))
tk.Label(author_hdr, text="AUTHORS",
         fg="#c084fc", bg="#1e293b",
         font=("Segoe UI", 11, "bold")).pack(side="left")

author_var = tk.StringVar()
make_copy_btn(author_hdr, stringvar=author_var).pack(side="right")

tk.Label(author_frame, textvariable=author_var,
         bg="#1e293b", fg="white",
         wraplength=240, justify="left",
         font=("Segoe UI", 10)).pack(padx=10, pady=8, anchor="w")

#full Summary
summary_frame = tk.Frame(main, bg="#1e293b")
summary_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 5), pady=(0, 6))

summary_hdr = tk.Frame(summary_frame, bg="#1e293b")
summary_hdr.pack(fill="x", padx=10, pady=(6, 0))
tk.Label(summary_hdr, text="FULL SUMMARY",
         fg="#c084fc", bg="#1e293b",
         font=("Segoe UI", 11, "bold")).pack(side="left")

summary_box = scrolledtext.ScrolledText(summary_frame,
                                        font=("Times New Roman", 13),
                                        wrap=tk.WORD,
                                        bg="#0f172a", fg="white", bd=0)
summary_box.pack(fill="both", expand=True, padx=10, pady=6)
summary_box.config(state="disabled")
make_copy_btn(summary_hdr, text_widget=summary_box).pack(side="right")

#iinsights
key_frame = tk.Frame(main, bg="#1e293b")
key_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 0), pady=(0, 6))

key_hdr = tk.Frame(key_frame, bg="#1e293b")
key_hdr.pack(fill="x", padx=10, pady=(6, 0))
tk.Label(key_hdr, text="KEY INSIGHTS",
         fg="#c084fc", bg="#1e293b",
         font=("Segoe UI", 11, "bold")).pack(side="left")

key_box = scrolledtext.ScrolledText(key_frame,
                                    font=("Segoe UI", 10),
                                    wrap=tk.WORD,
                                    bg="#0f172a", fg="white", bd=0)
key_box.pack(fill="both", expand=True, padx=10, pady=6)
key_box.config(state="disabled")
make_copy_btn(key_hdr, text_widget=key_box).pack(side="right")

# ── GRID WEIGHTS ─────────────────────────────
main.columnconfigure(0, weight=3)
main.columnconfigure(1, weight=2)
main.rowconfigure(1, weight=2)
main.rowconfigure(2, weight=3)

root.mainloop()