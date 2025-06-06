import sys, json, random, os, time
from datetime import datetime
from appdirs import user_data_dir
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QRadioButton,
    QHBoxLayout, QButtonGroup, QMessageBox, QStackedWidget, QFileDialog, QTabWidget, QScrollArea
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import shutil # Added for file copying

APP_NAME = "SATPrepApp"
APP_AUTHOR = "PSAT CBT"
DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "progress.json")
ANALYTICS_PATH = os.path.join(DATA_DIR, "analytics.json")

class SATPracticeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAT Practice CBT")
        self.resize(1000, 700)
        self.setFont(QFont("Arial", 12))

        # Apply global stylesheet for a more beautiful look
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8; /* Light gray background */
                font-family: Arial;
                color: #333; /* Dark gray text */
            }

            QLabel {
                color: #333;
                padding: 5px;
            }

            QPushButton {
                background-color: #4a90e2; /* Blue */
                color: white;
                border: none;
                border-radius: 8px; /* Rounded corners */
                padding: 12px 25px;
                margin: 5px 0;
                font-size: 16px;
                font-weight: bold;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2); /* Subtle shadow */
            }

            QPushButton:hover {
                background-color: #5b9bd5; /* Lighter blue on hover */
                box-shadow: 3px 3px 8px rgba(0, 0, 0, 0.3);
            }

            QPushButton:pressed {
                background-color: #3a7acb; /* Darker blue when pressed */
                box-shadow: 1px 1px 3px rgba(0, 0, 0, 0.2);
            }

            QRadioButton {
                font-size: 14px;
                padding: 5px 0;
            }

            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px; /* Make indicator circular */
                border: 2px solid #4a90e2; /* Blue border */
            }

            QRadioButton::indicator:checked {
                background-color: #4a90e2; /* Blue fill when checked */
                border: 2px solid #4a90e2;
            }

            QTabWidget::pane { /* The tab content frame */
                border: 1px solid #c2c7cb;
                border-radius: 8px;
                background-color: #ffffff;
            }

            QTabBar::tab {
                background: #e0e6eb; /* Lighter tab background */
                border: 1px solid #c2c7cb;
                border-bottom-color: #c2c7cb; /* Same as pane border */
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: bold;
            }

            QTabBar::tab:selected {
                background: #ffffff; /* White for selected tab */
                border-bottom-color: white; /* Make selected tab appear connected to pane */
            }

            QScrollArea {
                border: 1px solid #c2c7cb;
                border-radius: 8px;
                background-color: #ffffff;
            }

            QScrollArea > QWidget > QWidget { /* Content widget inside scroll area */
                background-color: #ffffff;
                padding: 10px;
            }
        """)

        # Load configurations and analytics
        self.load_config()
        self.load_analytics()

        # Initialize test state
        self.test_state = {
            "current_section": None,  # "RW" or "MATH"
            "current_module": None,   # e.g., "RW1", "RW2", "MATH1", "MATH2" (though current implementation only uses "RW", "MATH")
            "rw_index": 0,
            "math_index": 0,
            "user_answers": {"RW": {}, "MATH": {}},
            "start_time": None,
            "elapsed": 0,
            "test_phase": None,      # "RW", "MATH", "BREAK", "MENU"
        }

        # Timer setup
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.remaining_seconds = 0
        self.questions = [] # Initialize questions list

        # Load progress from previous session if available
        self.load_progress()

        # UI setup
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.stacked = QStackedWidget()
        self.main_layout.addWidget(self.stacked)

        # Create different screens
        self.menu_screen()
        self.test_screen()
        self.break_screen()
        self.review_screen()
        self.analytics_screen()

        # Set initial screen based on loaded progress
        if self.test_state["test_phase"] == "BREAK":
            self.start_break() # Go directly to break if interrupted during break
        elif self.test_state["current_section"]:
            # If current_section is set, attempt to resume the test
            self.start_test_section(self.test_state["current_section"], resume=True)
        else:
            self.stacked.setCurrentWidget(self.menu_widget)
            self.test_state["test_phase"] = "MENU" # Ensure phase is updated for menu

    def load_config(self):
        """
        Loads the application configuration from config.json.
        If the file doesn't exist or is corrupted, a default config is created.
        """
        default_config_data = {
            "question_banks": {
                "rw": os.path.join(DATA_DIR, "rw_questions.json"),
                "math": os.path.join(DATA_DIR, "math_questions.json")
            },
            "total_questions": {
                "rw": 27, # Default number of RW questions
                "math": 22 # Default number of Math questions
            },
            "default_time_limits": {
                "rw": 32, # Default time limit for RW in minutes
                "math": 35 # Default time limit for Math in minutes
            },
            "break_duration_minutes": 10 # Default break duration
        }

        def create_default_config():
            """Helper function to create and save the default config."""
            try:
                with open(CONFIG_PATH, "w") as f:
                    json.dump(default_config_data, f, indent=2)
                QMessageBox.information(self, "Config Created",
                    f"A default config has been created at:\n{CONFIG_PATH}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create default config: {str(e)}")
                return False

        if not os.path.exists(CONFIG_PATH):
            print(f"Config file not found at {CONFIG_PATH}. Creating default.")
            if not create_default_config():
                sys.exit(1) # Exit if cannot even create default config

        try:
            with open(CONFIG_PATH) as f:
                self.config = json.load(f)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Config Corrupted",
                f"The config file at {CONFIG_PATH} is corrupted or empty. It will be reset to default.")
            if os.path.exists(CONFIG_PATH):
                try:
                    os.remove(CONFIG_PATH) # Delete corrupted file
                    print(f"Removed corrupted config file: {CONFIG_PATH}")
                except Exception as e:
                    QMessageBox.warning(self, "File Error", f"Could not remove corrupted config file: {str(e)}")

            if not create_default_config(): # Try to create default again
                sys.exit(1) # Exit if cannot create default even after deleting corrupted one
            
            # After creating default, try loading it again
            try:
                with open(CONFIG_PATH) as f:
                    self.config = json.load(f)
            except Exception as e: # This should ideally not happen if create_default_config succeeded
                QMessageBox.critical(self, "Critical Error", f"Failed to load default config after reset: {str(e)}")
                sys.exit(1)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config: {str(e)}")
            sys.exit(1)

    def load_analytics(self):
        """
        Loads user analytics from analytics.json.
        Initializes default analytics if the file is not found or corrupted.
        """
        try:
            with open(ANALYTICS_PATH) as f:
                self.analytics = json.load(f)
        except FileNotFoundError:
            # Default analytics structure
            self.analytics = {
                "tests_taken": 0,
                "average_scores": {"RW": 0, "MATH": 0},
                "best_scores": {"RW": 0, "MATH": 0},
                "weakest_categories": {"RW": {}, "MATH": {}}, # Stores category: incorrect_count
                "progress_over_time": [], # Stores {"date": "YYYY-MM-DD", "scores": {"RW": X, "MATH": Y}}
            }
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Analytics Corrupted",
                f"The analytics file at {ANALYTICS_PATH} is corrupted or empty. It will be reset.")
            if os.path.exists(ANALYTICS_PATH):
                try:
                    os.remove(ANALYTICS_PATH)
                except Exception as e:
                    print(f"Error removing corrupted analytics file: {e}")
            self.analytics = { # Reset to default if corrupted
                "tests_taken": 0,
                "average_scores": {"RW": 0, "MATH": 0},
                "best_scores": {"RW": 0, "MATH": 0},
                "weakest_categories": {"RW": {}, "MATH": {}},
                "progress_over_time": [],
            }
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load analytics: {str(e)}\nInitializing with default analytics.")
            # Fallback to default analytics if load fails
            self.analytics = {
                "tests_taken": 0,
                "average_scores": {"RW": 0, "MATH": 0},
                "best_scores": {"RW": 0, "MATH": 0},
                "weakest_categories": {"RW": {}, "MATH": {}},
                "progress_over_time": [],
            }

    def save_analytics(self):
        """
        Saves the current analytics data to analytics.json.
        """
        try:
            with open(ANALYTICS_PATH, "w") as f:
                json.dump(self.analytics, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save analytics: {str(e)}")

    def update_analytics(self, rw_score_data, math_score_data):
        """
        Updates the analytics data after a test submission.
        rw_score_data: {'correct': int, 'total': int}
        math_score_data: {'correct': int, 'total': int}
        """
        self.analytics["tests_taken"] += 1

        # Calculate percentages
        rw_percentage = (rw_score_data['correct'] / rw_score_data['total']) * 100 if rw_score_data['total'] > 0 else 0
        math_percentage = (math_score_data['correct'] / math_score_data['total']) * 100 if math_score_data['total'] > 0 else 0

        # Update average scores
        current_rw_avg = self.analytics["average_scores"]["RW"]
        current_math_avg = self.analytics["average_scores"]["MATH"]
        num_tests = self.analytics["tests_taken"]

        # Simple moving average (or if you want a true average, you'd store sums and counts)
        # For simplicity, let's update average using direct calculation (assumes previous average was based on num_tests - 1)
        # More robust: keep track of total points and divide by total possible points
        # For now, let's just do a simple average considering new test
        self.analytics["average_scores"]["RW"] = ((current_rw_avg * (num_tests - 1)) + rw_percentage) / num_tests if num_tests > 0 else rw_percentage
        self.analytics["average_scores"]["MATH"] = ((current_math_avg * (num_tests - 1)) + math_percentage) / num_tests if num_tests > 0 else math_percentage


        # Update best scores
        self.analytics["best_scores"]["RW"] = max(self.analytics["best_scores"]["RW"], rw_percentage)
        self.analytics["best_scores"]["MATH"] = max(self.analytics["best_scores"]["MATH"], math_percentage)

        # Update weakest categories based on current test's incorrect answers
        # This requires iterating through the user's answers and comparing to correct answers
        # Ensure 'category' key exists in your question JSON for this to work effectively.
        all_sections_questions = {
            "RW": self.load_questions("RW", for_analytics=True), # Load all questions for analytics
            "MATH": self.load_questions("MATH", for_analytics=True)
        }

        for section_key, questions_list in all_sections_questions.items():
            for i, q in enumerate(questions_list):
                user_answer = self.test_state['user_answers'][section_key].get(i)
                correct_answer = q.get('answer')
                category = q.get('category', 'Uncategorized') # Default category if not provided

                if user_answer is not None and user_answer != correct_answer:
                    # Increment incorrect count for the category
                    self.analytics['weakest_categories'][section_key][category] = \
                        self.analytics['weakest_categories'][section_key].get(category, 0) + 1

        # Update progress over time
        self.analytics["progress_over_time"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "scores": {"RW": round(rw_percentage, 1), "MATH": round(math_percentage, 1)}
        })

        self.save_analytics() # Save analytics after updating

    def load_questions(self, section, for_analytics=False):
        """
        Loads questions for a given section. Randomly samples if not for analytics.
        'for_analytics=True' loads all questions without sampling for accurate analytics calculation.
        """
        path = self.config["question_banks"][section.lower()]
        try:
            with open(path) as f:
                data = json.load(f)
                questions = data.get("questions", [])

                # Validate questions: must have 'id', 'question', 'options', 'answer'
                valid_questions = [
                    q for q in questions
                    if all(key in q for key in ['id', 'question', 'options', 'answer'])
                ]

                if not valid_questions:
                    QMessageBox.critical(self, "Error", f"No valid questions found in {section} question bank: {path}")
                    return []

                if for_analytics:
                    return valid_questions # Return all questions for analytics (to check all answers)
                else:
                    total_needed = self.config["total_questions"][section.lower()]
                    # Sample questions if there are enough, otherwise return all valid ones
                    return random.sample(valid_questions, min(len(valid_questions), total_needed))

        except FileNotFoundError:
            QMessageBox.critical(self, "Error",
                f"Question bank file not found for {section} section:\n{path}\n"
                "Please ensure the file exists or update your config.json.")
            return []
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error",
                f"Invalid JSON in {section} question bank file:\n{path}\n"
                "Please check the file's format.")
            return []
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to load {section} questions from {path}:\n{str(e)}")
            return []

    def menu_screen(self):
        """Sets up the main menu screen."""
        self.menu_widget = QWidget()
        layout = QVBoxLayout()
        self.menu_widget.setLayout(layout)

        title = QLabel("SAT Practice Test")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addStretch(1) # Add stretch to push buttons to center

        start_btn = QPushButton("Start Full Test")
        start_btn.setFont(QFont("Arial", 16))
        start_btn.setMinimumHeight(50)
        layout.addWidget(start_btn)
        start_btn.clicked.connect(self.start_full_test)

        analytics_btn = QPushButton("View Analytics")
        analytics_btn.setFont(QFont("Arial", 16))
        analytics_btn.setMinimumHeight(50)
        layout.addWidget(analytics_btn)
        analytics_btn.clicked.connect(lambda: self.stacked.setCurrentWidget(self.analytics_widget))

        layout.addStretch(1) # Add stretch

        self.stacked.addWidget(self.menu_widget)

    def test_screen(self):
        """Sets up the test screen layout."""
        self.test_widget = QWidget()
        v_layout = QVBoxLayout()
        self.test_widget.setLayout(v_layout)

        # Section label
        self.section_label = QLabel("")
        self.section_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.section_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        v_layout.addWidget(self.section_label)

        # Timer label
        self.timer_label = QLabel("Time left: 00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        v_layout.addWidget(self.timer_label)

        # Scroll area for question text to handle long questions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.question_label = QLabel("Question text")
        self.question_label.setWordWrap(True)
        self.question_label.setFont(QFont("Arial", 14))
        scroll_area.setWidget(self.question_label)
        v_layout.addWidget(scroll_area)

        # Answer choices
        self.choices_group = QButtonGroup(self)
        self.choices_group.setExclusive(True)
        self.choices_buttons = []
        for i in range(4): # Assuming A, B, C, D options
            rb = QRadioButton("")
            rb.setFont(QFont("Arial", 14))
            v_layout.addWidget(rb)
            self.choices_group.addButton(rb, i)
            self.choices_buttons.append(rb)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.setFont(QFont("Arial", 14))
        self.next_btn.setFont(QFont("Arial", 14))
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        v_layout.addLayout(nav_layout)

        # Submit button
        self.submit_btn = QPushButton("Submit Section")
        self.submit_btn.setFont(QFont("Arial", 14))
        self.submit_btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 8px; padding: 12px 25px;") # Green background
        v_layout.addWidget(self.submit_btn)

        # Connect signals
        self.prev_btn.clicked.connect(self.prev_question)
        self.next_btn.clicked.connect(self.next_question)
        self.submit_btn.clicked.connect(self.submit_section)
        self.choices_group.buttonClicked.connect(self.save_answer)

        self.stacked.addWidget(self.test_widget)

    def break_screen(self):
        """Sets up the break screen layout."""
        self.break_widget = QWidget()
        layout = QVBoxLayout()
        self.break_widget.setLayout(layout)

        layout.addStretch(1)

        self.break_label = QLabel("Break Time")
        self.break_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.break_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(self.break_label)

        self.break_timer_label = QLabel("Break time remaining: 10:00")
        self.break_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.break_timer_label.setFont(QFont("Arial", 20))
        layout.addWidget(self.break_timer_label)

        layout.addSpacing(40)

        self.continue_btn = QPushButton("Continue to Next Section")
        self.continue_btn.setFont(QFont("Arial", 16))
        self.continue_btn.setMinimumHeight(50)
        self.continue_btn.setStyleSheet("background-color: #008CBA; color: white; border-radius: 8px; padding: 12px 25px;") # Blue background
        layout.addWidget(self.continue_btn)
        self.continue_btn.clicked.connect(self.start_next_section)

        layout.addStretch(1)

        self.stacked.addWidget(self.break_widget)

    def review_screen(self):
        """Sets up the test review and results screen layout."""
        self.review_widget = QWidget()
        self.review_layout = QVBoxLayout()
        self.review_widget.setLayout(self.review_layout)

        self.review_title = QLabel("Test Results")
        self.review_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.review_title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.review_layout.addWidget(self.review_title)

        self.review_tabs = QTabWidget()
        self.review_layout.addWidget(self.review_tabs)

        # --- Summary Tab ---
        self.summary_tab = QWidget()
        self.summary_layout = QVBoxLayout()
        self.summary_tab.setLayout(self.summary_layout)

        self.scores_layout = QHBoxLayout()
        self.summary_layout.addLayout(self.scores_layout)

        self.rw_score_label = QLabel("Reading/Writing: -")
        self.rw_score_label.setFont(QFont("Arial", 16))
        self.scores_layout.addWidget(self.rw_score_label)

        self.math_score_label = QLabel("Math: -")
        self.math_score_label.setFont(QFont("Arial", 16))
        self.scores_layout.addWidget(self.math_score_label)

        self.performance_label = QLabel()
        self.performance_label.setFont(QFont("Arial", 14))
        self.performance_label.setWordWrap(True)
        self.summary_layout.addWidget(self.performance_label)

        self.weak_areas_label = QLabel()
        self.weak_areas_label.setFont(QFont("Arial", 14))
        self.weak_areas_label.setWordWrap(True)
        self.summary_layout.addWidget(self.weak_areas_label)

        # --- Detailed Reviews Tab ---
        self.details_tab = QWidget()
        self.details_layout = QVBoxLayout()
        self.details_tab.setLayout(self.details_layout)

        self.review_scroll_area = QScrollArea()
        self.review_scroll_area.setWidgetResizable(True)
        self.review_content_widget = QWidget()
        self.review_list_layout = QVBoxLayout(self.review_content_widget)
        self.review_scroll_area.setWidget(self.review_content_widget)
        self.details_layout.addWidget(self.review_scroll_area)


        self.review_tabs.addTab(self.summary_tab, "Summary")
        self.review_tabs.addTab(self.details_tab, "Detailed Review")

        self.save_results_btn = QPushButton("Save Results to File")
        self.save_results_btn.setFont(QFont("Arial", 14))
        self.review_layout.addWidget(self.save_results_btn)
        self.save_results_btn.clicked.connect(self.save_results)

        self.back_to_menu_btn = QPushButton("Back to Menu")
        self.back_to_menu_btn.setFont(QFont("Arial", 14))
        self.review_layout.addWidget(self.back_to_menu_btn)
        self.back_to_menu_btn.clicked.connect(self.back_to_menu)

        self.stacked.addWidget(self.review_widget)

    def analytics_screen(self):
        """Sets up the analytics screen layout."""
        self.analytics_widget = QWidget()
        layout = QVBoxLayout()
        self.analytics_widget.setLayout(layout)

        title = QLabel("Performance Analytics")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # - Overall Stats Tab 
        overall_tab = QWidget()
        overall_layout = QVBoxLayout()
        overall_tab.setLayout(overall_layout)

        self.analytics_tests_taken_label = QLabel(f"Tests Completed: {self.analytics['tests_taken']}")
        self.analytics_tests_taken_label.setFont(QFont("Arial", 14))
        overall_layout.addWidget(self.analytics_tests_taken_label)

        self.analytics_avg_label = QLabel("Average Scores:\nReading/Writing: 0.0%\nMath: 0.0%")
        self.analytics_avg_label.setFont(QFont("Arial", 14))
        overall_layout.addWidget(self.analytics_avg_label)

        self.analytics_best_label = QLabel("Best Scores:\nReading/Writing: 0%\nMath: 0%")
        self.analytics_best_label.setFont(QFont("Arial", 14))
        overall_layout.addWidget(self.analytics_best_label)

        # -- Weak Areas Tab 
        weak_tab = QWidget()
        self.weak_layout_content = QVBoxLayout() # Use a separate layout for dynamic content
        weak_tab.setLayout(self.weak_layout_content)

        # - Progress Tab 
        progress_tab = QWidget()
        self.progress_layout_content = QVBoxLayout() # Use a separate layout for dynamic content
        progress_tab.setLayout(self.progress_layout_content)


        tabs.addTab(overall_tab, "Overall Stats")
        tabs.addTab(weak_tab, "Weak Areas")
        tabs.addTab(progress_tab, "Progress")

        # Back button
        back_btn = QPushButton("Back to Menu")
        back_btn.setFont(QFont("Arial", 14))
        layout.addWidget(back_btn)
        back_btn.clicked.connect(lambda: self.stacked.setCurrentWidget(self.menu_widget))
        back_btn.clicked.connect(self.update_analytics_display) # Update analytics display on return

        self.stacked.addWidget(self.analytics_widget)

    def update_analytics_display(self):
        """Updates the labels on the analytics screen with current data."""
        self.analytics_tests_taken_label.setText(f"Tests Completed: {self.analytics['tests_taken']}")

        rw_avg = self.analytics['average_scores']['RW']
        math_avg = self.analytics['average_scores']['MATH']
        self.analytics_avg_label.setText(f"Average Scores:\nReading/Writing: {rw_avg:.1f}%\nMath: {math_avg:.1f}%")

        rw_best = self.analytics['best_scores']['RW']
        math_best = self.analytics['best_scores']['MATH']
        self.analytics_best_label.setText(f"Best Scores:\nReading/Writing: {rw_best:.1f}%\nMath: {math_best:.1f}%") # Display with .1f for consistency

        # Clears the existing weak area labels
        for i in reversed(range(self.weak_layout_content.count())):
            widget = self.weak_layout_content.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Adds updated weak area labels
        rw_weak_label = QLabel("Reading/Writing Weak Areas:")
        rw_weak_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.weak_layout_content.addWidget(rw_weak_label)
        if not self.analytics['weakest_categories']['RW']:
            self.weak_layout_content.addWidget(QLabel("No data yet."))
        else:
            for category, count in sorted(self.analytics['weakest_categories']['RW'].items(), key=lambda item: item[1], reverse=True):
                self.weak_layout_content.addWidget(QLabel(f"- {category}: {count} incorrect"))

        math_weak_label = QLabel("\nMath Weak Areas:")
        math_weak_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.weak_layout_content.addWidget(math_weak_label)
        if not self.analytics['weakest_categories']['MATH']:
            self.weak_layout_content.addWidget(QLabel("No data yet."))
        else:
            for category, count in sorted(self.analytics['weakest_categories']['MATH'].items(), key=lambda item: item[1], reverse=True):
                self.weak_layout_content.addWidget(QLabel(f"- {category}: {count} incorrect"))

        # Clear existing progress labels
        for i in reversed(range(self.progress_layout_content.count())):
            widget = self.progress_layout_content.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Add updated progress labels
        progress_label = QLabel("Progress Over Time:")
        progress_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.progress_layout_content.addWidget(progress_label)

        if not self.analytics['progress_over_time']:
            self.progress_layout_content.addWidget(QLabel("No test history yet."))
        else:
            for entry in self.analytics['progress_over_time'][-5:]: # Shows last 5 tests
                date_str = entry['date']
                rw_score = entry['scores']['RW']
                math_score = entry['scores']['MATH']
                self.progress_layout_content.addWidget(QLabel(f"{date_str}: RW {rw_score}%, Math {math_score}%"))

    def start_full_test(self):
        """Initiates a full test by resetting state and starting the RW section."""
        # Resets test state
        self.test_state = {
            "current_section": "RW",
            "current_module": "RW1", # Keep this for potential future module breakdown
            "rw_index": 0,
            "math_index": 0,
            "user_answers": {"RW": {}, "MATH": {}},
            "start_time": None,
            "elapsed": 0,
            "test_phase": "RW", # Indicate current phase
        }
        self.questions = [] # Clear previous questions
        self.save_progress(delete=True) # Clear any old progress
        self.start_test_section("RW")

    def start_test_section(self, section, resume=False):
        """
        Starts or resumes a test section (RW or MATH).
        'resume' flag determines if questions are reloaded or use existing ones.
        """
        self.test_state["current_section"] = section
        self.test_state["test_phase"] = section # Set test phase to current section

        if not resume:
            self.test_state["start_time"] = time.time()
            self.test_state["elapsed"] = 0
            self.questions = self.load_questions(section)
            if not self.questions:
                QMessageBox.critical(self, "Error", f"Could not start {section} section: No valid questions loaded.")
                self.stacked.setCurrentWidget(self.menu_widget)
                self.test_state["test_phase"] = "MENU"
                return

            self.remaining_seconds = self.config["default_time_limits"][section.lower()] * 60
            # Reset index to 0 for a new section start
            if section == "RW":
                self.test_state["rw_index"] = 0
            else:
                self.test_state["math_index"] = 0
        else:
            # If resuming, 'self.questions' and 'remaining_seconds' are loaded from save_progress
            if not self.questions: # Fallback if questions weren't saved properly
                QMessageBox.critical(self, "Error", f"Failed to resume {section} section: No questions loaded from progress. Starting new section.")
                self.questions = self.load_questions(section)
                if not self.questions:
                    self.stacked.setCurrentWidget(self.menu_widget)
                    self.test_state["test_phase"] = "MENU"
                    return
                # Reset timer if questions had to be reloaded, use default time
                self.remaining_seconds = self.config["default_time_limits"][section.lower()] * 60


        self.timer.start(1000) # Start the timer

        # Set section label
        section_name = "Reading and Writing" if section == "RW" else "Math"
        self.section_label.setText(f"{section_name} Section")

        self.show_question() # Display the current question

        self.stacked.setCurrentWidget(self.test_widget)
        self.save_progress() # Save progress after starting section

    def update_timer(self):
        """Updates the timer display and handles time-up scenarios."""
        if self.remaining_seconds <= 0:
            self.timer.stop()
            QMessageBox.information(self, "Time's up!", "The time limit has been reached for this section.")
            self.submit_section()
            return
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.setText(f"Time left: {mins:02d}:{secs:02d}")
        self.remaining_seconds -= 1

        # Only save progress during active test phase to avoid issues during breaks/menus
        if self.test_state["test_phase"] in ["RW", "MATH"]:
            self.save_progress()

    def current_index(self):
        """Returns the current question index for the active section."""
        return self.test_state["rw_index"] if self.test_state["current_section"] == "RW" else self.test_state["math_index"]

    def set_current_index(self, val):
        """Sets the current question index for the active section."""
        if self.test_state["current_section"] == "RW":
            self.test_state["rw_index"] = val
        else:
            self.test_state["math_index"] = val
        self.save_progress() # Save progress after changing question

    def show_question(self):
        """Displays the current question and its answer choices."""
        idx = self.current_index()
        if not self.questions or idx >= len(self.questions):
            QMessageBox.critical(self, "Error", "No question to display. Please check question banks.")
            self.back_to_menu()
            return

        q = self.questions[idx]
        self.question_label.setText(f"Q{idx + 1}: {q['question']}")

        # Populate and show/hide radio buttons based on available options
        for i, rb in enumerate(self.choices_buttons):
            if i < len(q["options"]):
                rb.setText(q["options"][i])
                rb.show()
            else:
                rb.hide()

        # Load user's previously saved answer for the current question
        section = self.test_state["current_section"]
        ans = self.test_state["user_answers"][section].get(idx)
        if ans is not None:
            # Convert 'A', 'B', 'C', 'D' back to 0, 1, 2, 3
            try:
                selected_idx = ord(ans) - ord('A')
                if 0 <= selected_idx < len(self.choices_buttons):
                    self.choices_buttons[selected_idx].setChecked(True)
                else: # Fallback if saved answer is invalid
                    self.choices_group.setExclusive(False)
                    for rb in self.choices_buttons:
                        rb.setChecked(False)
                    self.choices_group.setExclusive(True)
            except TypeError: # Handle case if ans is not a character
                self.choices_group.setExclusive(False)
                for rb in self.choices_buttons:
                    rb.setChecked(False)
                self.choices_group.setExclusive(True)
        else:
            # Clear selection if no answer was saved for this question
            self.choices_group.setExclusive(False)
            for rb in self.choices_buttons:
                rb.setChecked(False)
            self.choices_group.setExclusive(True)

        # Enable/disable navigation buttons
        self.prev_btn.setDisabled(idx == 0)
        self.next_btn.setDisabled(idx == len(self.questions) - 1)

    def save_answer(self):
        """Saves the user's selected answer for the current question."""
        btn = self.choices_group.checkedButton()
        if btn:
            idx = self.current_index()
            section = self.test_state["current_section"]
            # Convert button ID (0, 1, 2, 3) to 'A', 'B', 'C', 'D'
            answer = chr(ord('A') + self.choices_group.id(btn))
            self.test_state["user_answers"][section][idx] = answer
            self.save_progress() # Save progress immediately after an answer is saved

    def prev_question(self):
        """Navigates to the previous question."""
        idx = self.current_index()
        if idx > 0:
            self.set_current_index(idx - 1)
            self.show_question()

    def next_question(self):
        """Navigates to the next question."""
        idx = self.current_index()
        if idx < len(self.questions) - 1:
            self.set_current_index(idx + 1)
            self.show_question()

    def submit_section(self):
        """Handles the submission of a test section."""
        self.timer.stop()

        reply = QMessageBox.question(self, "Submit Section", "Are you sure you want to submit this section?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            current_section = self.test_state["current_section"]

            if current_section == "RW":
                # After RW, transition to break, then Math
                self.start_break()
            else: # current_section == "MATH"
                # After Math, end of test, show results
                self.show_results()
        else:
            self.timer.start(1000) # Resume timer if user cancels submission

    def start_break(self):
        """Initiates the break period between sections."""
        self.test_state["test_phase"] = "BREAK"
        self.remaining_seconds = self.config.get("break_duration_minutes", 10) * 60 # Default to 10 minutes
        self.timer.start(1000)
        self.break_label.setText("Break Time - Next: Math Section")
        self.stacked.setCurrentWidget(self.break_widget)
        self.save_progress() # Save progress at start of break

    def start_next_section(self):
        """Continues to the next section after a break."""
        self.timer.stop()
        self.test_state["test_phase"] = "MATH"
        self.start_test_section("MATH")

    def show_results(self):
        """Calculates and displays test results, and updates analytics."""
        self.timer.stop() # Ensure timer is stopped

        # Load all original questions for accurate scoring and analytics (not just sampled ones)
        rw_all_questions = self.load_questions("RW", for_analytics=True)
        math_all_questions = self.load_questions("MATH", for_analytics=True)

        # Calculate scores
        rw_correct = sum(1 for i, q in enumerate(rw_all_questions)
                      if self.test_state['user_answers']['RW'].get(i) == q.get('answer'))
        math_correct = sum(1 for i, q in enumerate(math_all_questions)
                       if self.test_state['user_answers']['MATH'].get(i) == q.get('answer'))

        rw_total = len(rw_all_questions)
        math_total = len(math_all_questions)

        # Prepare score data for analytics
        rw_score_data = {'correct': rw_correct, 'total': rw_total}
        math_score_data = {'correct': math_correct, 'total': math_total}

        # Update analytics
        self.update_analytics(rw_score_data, math_score_data)

        # Update review screen labels
        rw_percentage = (rw_correct / rw_total) * 100 if rw_total > 0 else 0
        math_percentage = (math_correct / math_total) * 100 if math_total > 0 else 0

        self.rw_score_label.setText(f"Reading/Writing: {rw_correct} / {rw_total} ({rw_percentage:.0f}%)")
        self.math_score_label.setText(f"Math: {math_correct} / {math_total} ({math_percentage:.0f}%)")

        performance_text = f"""
        Performance Summary:
        - Reading/Writing: {rw_correct} of {rw_total} correct ({rw_percentage:.0f}%)
        - Math: {math_correct} of {math_total} correct ({math_percentage:.0f}%)
        """
        self.performance_label.setText(performance_text)

        # Update weak areas display using analytics data
        weak_text = "Weakest Areas (by count of incorrect answers):\n"
        rw_weak = sorted(self.analytics['weakest_categories']['RW'].items(), key=lambda x: x[1], reverse=True)
        math_weak = sorted(self.analytics['weakest_categories']['MATH'].items(), key=lambda x: x[1], reverse=True)

        if rw_weak:
            weak_text += "Reading/Writing:\n"
            for cat, count in rw_weak[:3]: # Show top 3 weakest categories
                weak_text += f"- {cat}: {count} incorrect\n"
        else:
            weak_text += "Reading/Writing: No categorized incorrect answers yet.\n"

        if math_weak:
            weak_text += "\nMath:\n"
            for cat, count in math_weak[:3]: # Show top 3 weakest categories
                weak_text += f"- {cat}: {count} incorrect\n"
        else:
            weak_text += "\nMath: No categorized incorrect answers yet."

        self.weak_areas_label.setText(weak_text)

        # Populate detailed review section
        # Clear existing review items
        for i in reversed(range(self.review_list_layout.count())):
            widget = self.review_list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Add detailed review for RW section
        for idx, q in enumerate(rw_all_questions):
            user_ans = self.test_state['user_answers']['RW'].get(idx, "N/A")
            correct_ans = q.get('answer', "N/A")
            correct = (user_ans == correct_ans)
            lbl = QLabel(f"Q{idx + 1} (RW): {q.get('question', 'N/A')}\n"
                         f"Your answer: {user_ans} | Correct: {correct_ans}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: green;" if correct else "color: red;")
            self.review_list_layout.addWidget(lbl)
            self.review_list_layout.addWidget(QLabel("-" * 50)) # Separator

        # Add detailed review for Math section
        for idx, q in enumerate(math_all_questions):
            user_ans = self.test_state['user_answers']['MATH'].get(idx, "N/A")
            correct_ans = q.get('answer', "N/A")
            correct = (user_ans == correct_ans)
            lbl = QLabel(f"Q{idx + 1} (MATH): {q.get('question', 'N/A')}\n"
                         f"Your answer: {user_ans} | Correct: {correct_ans}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: green;" if correct else "color: red;")
            self.review_list_layout.addWidget(lbl)
            self.review_list_layout.addWidget(QLabel("-" * 50)) # Separator

        # Clear progress file after test completion
        self.save_progress(delete=True)

        self.stacked.setCurrentWidget(self.review_widget)

    def save_results(self):
        """Saves the detailed test results to a JSON file chosen by the user."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "JSON Files (*.json)")
        if not filename:
            return

        # Load all original questions to ensure full detail in saved results
        rw_all_questions = self.load_questions("RW", for_analytics=True)
        math_all_questions = self.load_questions("MATH", for_analytics=True)

        detailed_rw_answers = []
        for i, q in enumerate(rw_all_questions):
            user_ans = self.test_state['user_answers']['RW'].get(i, "N/A")
            correct_ans = q.get('answer', "N/A")
            detailed_rw_answers.append({
                "question_id": q.get('id', 'N/A'),
                "question_text": q.get('question', 'N/A'),
                "options": q.get('options', []),
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": (user_ans == correct_ans),
                "category": q.get('category', 'Uncategorized')
            })

        detailed_math_answers = []
        for i, q in enumerate(math_all_questions):
            user_ans = self.test_state['user_answers']['MATH'].get(i, "N/A")
            correct_ans = q.get('answer', "N/A")
            detailed_math_answers.append({
                "question_id": q.get('id', 'N/A'),
                "question_text": q.get('question', 'N/A'),
                "options": q.get('options', []),
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": (user_ans == correct_ans),
                "category": q.get('category', 'Uncategorized')
            })

        results = {
            "timestamp": datetime.now().isoformat(),
            "reading_writing_section": {
                "score": sum(1 for a in detailed_rw_answers if a['is_correct']),
                "total_questions": len(detailed_rw_answers),
                "detailed_answers": detailed_rw_answers
            },
            "math_section": {
                "score": sum(1 for a in detailed_math_answers if a['is_correct']),
                "total_questions": len(detailed_math_answers),
                "detailed_answers": detailed_math_answers
            }
        }

        try:
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)
            QMessageBox.information(self, "Success", f"Results saved successfully to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save results:\n{e}")

    def back_to_menu(self):
        """Resets test state and returns to the main menu."""
        self.timer.stop() # Stop any active timers
        self.test_state = { # Reset to initial state
            "current_section": None,
            "current_module": None,
            "rw_index": 0,
            "math_index": 0,
            "user_answers": {"RW": {}, "MATH": {}},
            "start_time": None,
            "elapsed": 0,
            "test_phase": "MENU", # Set phase to menu
        }
        self.questions = [] # Clear questions from memory
        self.save_progress(delete=True) # Ensure progress is cleared
        self.stacked.setCurrentWidget(self.menu_widget)

    def save_progress(self, delete=False):
        """
        Saves the current test progress to a JSON file.
        If delete is True, the progress file is removed.
        """
        if delete:
            if os.path.exists(PROGRESS_PATH):
                try:
                    os.remove(PROGRESS_PATH)
                except Exception as e:
                    print(f"Error deleting progress file: {e}") # Log error, don't crash
            return

        data = {
            "test_state": self.test_state,
            "questions": self.questions, # Save the current set of sampled questions
            "remaining_seconds": self.remaining_seconds,
        }
        try:
            with open(PROGRESS_PATH, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving progress: {e}") # Log error, silently ignore to not disrupt flow

    def load_progress(self):
        """
        Loads previous test progress from progress.json.
        Prompts the user to resume if progress is found.
        """
        if not os.path.exists(PROGRESS_PATH):
            return

        reply = QMessageBox.question(self, "Resume Test?",
                                     "Previous test progress found. Resume?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(PROGRESS_PATH) as f:
                    data = json.load(f)
                    self.test_state = data.get("test_state", self.test_state)
                    self.questions = data.get("questions", [])
                    self.remaining_seconds = data.get("remaining_seconds", 0)

                    # Ensure test_state keys are present even if not saved (for older progress files)
                    self.test_state.setdefault("user_answers", {"RW": {}, "MATH": {}})
                    self.test_state.setdefault("rw_index", 0)
                    self.test_state.setdefault("math_index", 0)
                    self.test_state.setdefault("test_phase", None) # Default to None if not present

                    # If we were in a break, go back to the break screen
                    if self.test_state.get("test_phase") == "BREAK":
                        # The __init__ will call start_break if test_phase is BREAK
                        pass
                    elif self.test_state["current_section"]:
                        # The __init__ will call start_test_section if current_section is set
                        pass
                    # If we load progress but section/phase aren't set, it will default to menu in __init__

            except json.JSONDecodeError:
                QMessageBox.warning(self, "Load Progress Error", f"The progress file at {PROGRESS_PATH} is corrupted or empty. Starting a new test.")
                self.save_progress(delete=True) # Delete corrupted progress file
                # Reset test state to ensure a clean start if load fails
                self.test_state = {
                    "current_section": None, "current_module": None,
                    "rw_index": 0, "math_index": 0,
                    "user_answers": {"RW": {}, "MATH": {}},
                    "start_time": None, "elapsed": 0, "test_phase": None,
                }
            except Exception as e:
                QMessageBox.warning(self, "Load Progress Error", f"Failed to load previous progress: {str(e)}\nStarting a new test.")
                self.save_progress(delete=True) # Delete corrupted progress file
                # Reset test state to ensure a clean start if load fails
                self.test_state = {
                    "current_section": None, "current_module": None,
                    "rw_index": 0, "math_index": 0,
                    "user_answers": {"RW": {}, "MATH": {}},
                    "start_time": None, "elapsed": 0, "test_phase": None,
                }
        else:
            # If user chooses not to resume, clear the progress file
            self.save_progress(delete=True)


if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_questions_dir = os.path.join(script_dir, "default_questions")

    # Define paths for default question bank files in the DATA_DIR
    rw_dest_path = os.path.join(DATA_DIR, "rw_questions.json")
    math_dest_path = os.path.join(DATA_DIR, "math_questions.json")

    # Define paths for source default question bank files
    rw_source_path = os.path.join(default_questions_dir, "rw_questions.json")
    math_source_path = os.path.join(default_questions_dir, "math_questions.json")

    # Check if DATA_DIR question banks exist, if not, try to copy from default_questions
    if not os.path.exists(rw_dest_path):
        if os.path.exists(rw_source_path):
            try:
                shutil.copy(rw_source_path, rw_dest_path)
                print(f"Copied default RW questions from {rw_source_path} to {rw_dest_path}")
            except Exception as e:
                print(f"Error copying default RW questions: {e}")
        else:
            print(f"Default RW questions not found at {rw_source_path}. Creating dummy.")
            # Creates dummy questions if default source is also missing (fallback)
            dummy_rw_questions = {
                "questions": [
                    {"id": "RW1", "question": "What is the main idea of a text?", "options": ["A. The topic", "B. The author's purpose", "C. The central point", "D. The concluding sentence"], "answer": "C", "category": "Main Idea"},
                    {"id": "RW2", "question": "Which word means 'generous'?", "options": ["A. Stingy", "B. Altruistic", "C. Selfish", "D. Greedy"], "answer": "B", "category": "Vocabulary"},
                    {"id": "RW3", "question": "Identify the independent clause: 'After the rain stopped, the sun came out.'", "options": ["A. After the rain stopped", "B. the rain stopped", "C. the sun came out", "D. After the rain stopped, the sun came out"], "answer": "C", "category": "Sentence Structure"},
                    {"id": "RW4", "question": "Which of the following is an example of a simile?", "options": ["A. The moon smiled.", "B. She was as brave as a lion.", "C. The car was a beast.", "D. The wind whispered secrets."], "answer": "B", "category": "Literary Devices"},
                    {"id": "RW5", "question": "What is the purpose of a thesis statement?", "options": ["A. To summarize the conclusion", "B. To introduce the topic", "C. To state the main argument of an essay", "D. To provide supporting evidence"], "answer": "C", "category": "Essay Structure"}
                ]
            }
            with open(rw_dest_path, "w") as f:
                json.dump(dummy_rw_questions, f, indent=2)

    if not os.path.exists(math_dest_path):
        if os.path.exists(math_source_path):
            try:
                shutil.copy(math_source_path, math_dest_path)
                print(f"Copied default Math questions from {math_source_path} to {math_dest_path}")
            except Exception as e:
                print(f"Error copying default Math questions: {e}")
        else:
            print(f"Default Math questions not found at {math_source_path}. Creating dummy.")
            # Creates dummy questions if default source is also missing (fallback)
            dummy_math_questions = {
                "questions": [
                    {"id": "M1", "question": "If 2x + 5 = 11, what is x?", "options": ["A. 2", "B. 3", "C. 4", "D. 5"], "answer": "B", "category": "Algebra"},
                    {"id": "M2", "question": "What is the area of a rectangle with length 8 and width 4?", "options": ["A. 12", "B. 16", "C. 24", "D. 32"], "answer": "D", "category": "Geometry"},
                    {"id": "M3", "question": "Solve for y: 3(y - 2) = 9", "options": ["A. 3", "B. 4", "C. 5", "D. 6"], "answer": "C", "category": "Equations"},
                    {"id": "M4", "question": "If a car travels at 60 miles per hour, how far does it travel in 2.5 hours?", "options": ["A. 120 miles", "B. 150 miles", "C. 180 miles", "D. 200 miles"], "answer": "B", "category": "Word Problems"},
                    {"id": "M5", "question": "What is 15% of 200?", "options": ["A. 20", "B. 30", "C. 40", "D. 50"], "answer": "B", "category": "Percentages"}
                ]
            }
            with open(math_dest_path, "w") as f:
                json.dump(dummy_math_questions, f, indent=2)

    app = QApplication(sys.argv)
    window = SATPracticeApp()
    window.show()
    sys.exit(app.exec())

    # Made with love and insomnia for free usage and distribution
    # Please ensure all modules agree with each other before pushing updates
    # We are in dire need of a complete question bank
