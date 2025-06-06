---
# SATPrepApp

A basic and lightweight, offline SAT Practice App that simulates the test environment, tracks your progress, and highlights your strengths and weaknesses. Designed for students who want a focused, distraction-free study tool.

---

# ⚠️Disclaimer
We are in no way affiliated with the [College board](https://www.collegeboard.org/) , we only incoporate official past SAT questions made publicly available by the [College board](https://www.collegeboard.org/).

---
## 📦 What This App Does

* Presents SAT-style questions in a timed, sectioned format
* Supports Reading/Writing and Math sections
* Automatically saves progress so you can resume later
* Analyzes your performance over time
* Identifies your weakest categories
* Lets you save results to a file for review
* Runs effectively on cross platforms

---

## 🔧 Installation & Requirements

### Python 3.9+

Install dependencies:

```bash
pip install PyQt6 appdirs
```
 
---
update python:

```bash
pip update Python3 #or just Python
```

---

Don't have python installed?
 click [here](https://www.python.org/downloads/)

 ---

## 🚀 Running the App

```bash
#locate the directory in which it is downloaded (eg: cd downloads), then run:

python satprepapp.py
```

If it's your first time launching, the app will automatically create a default config file in a platform-appropriate location:

* **Windows**: `C:\Users\<YourName>\AppData\Roaming\SATPrepApp\`
* **macOS**: `~/Library/Application Support/SATPrepApp/`
* **Linux**: `~/.local/share/SATPrepApp/`

This folder will contain:

* `config.json` — contains paths to your question banks and settings
* `progress.json` — saves your current test state
* `analytics.json` — stores your test history and performance trends

---

##  Adding Your Questions

Update the `config.json` file to point to your own question banks. The format should look like this:

```json
{
  "question_banks": {
    "rw": "/path/to/your/reading_writing.json",
    "math": "/path/to/your/math.json"
  },
  "total_questions": {
    "rw": 27,
    "math": 22
  },
  "default_time_limits": {
    "rw": 32,
    "math": 35
  }
}
```

Each question bank file should look like:

```json
{
  "questions": [
    {
      "id": 1,
      "question": "What is the value of x in 2x + 3 = 7?",
      "options": ["1", "2", "3", "4"],
      "answer": "B"
    },
    ...
  ]
}
```

The main question banks will be added later on, as compiling 600+ questions into a json file isn't an easy feat.

## Features That Matter

* **Auto Resume**: Automatically saves your test in progress so you never lose work.
* **Analytics**: Tracks your scores over time and shows your weakest subjects.
* **Detailed Review**: See which questions you got right or wrong and what the correct answers were.

---

## 🛠️ Built With

* [PyQt6](https://pypi.org/project/PyQt6/) - for GUI
* [appdirs](https://pypi.org/project/appdirs/) - for cross-platform file paths
* \[JSON] - for configs and question data
* [Python](https://python.org)  - duhh, it's a python script!

---

## ❤️ Notes

This project was made with love (and insomnia). You are free to modify and redistribute it with acquired permission.

An executable will be provided soon... in the mean while you can run the python script or create your own executable

Please ensure your question bank files follow the correct format — mismatches will prevent questions from loading.

Pull requests, issues, and feedback are welcome!;
Chat with me on [telegram](https://t.me/jayjaylovescandles),if you want to contribute or need assistance (i'm not always available though..)
