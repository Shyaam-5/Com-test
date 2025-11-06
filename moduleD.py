import random
from typing import List, Dict, Optional, Union

# Extended question bank
questions_bank = [
    {"sentence": "She ___ going to the market.", "answer": "is", "category": "be_verb"},
    {"sentence": "They have been friends ___ childhood.", "answer": "since", "category": "preposition"},
    {"sentence": "He runs faster ___ anyone else.", "answer": "than", "category": "comparison"},
    {"sentence": "I have lived here ___ five years.", "answer": "for", "category": "preposition"},
    {"sentence": "This is the ___ book I have ever read.", "answer": "best", "category": "superlative"},
    {"sentence": "I am looking forward ___ meeting you.", "answer": "to", "category": "phrasal_verb"},
    {"sentence": "Neither the teacher nor the students ___ ready.", "answer": "are", "category": "subject_verb"},
    {"sentence": "She has been working here ___ last year.", "answer": "since", "category": "preposition"},
    {"sentence": "We went to the park ___ it was raining.", "answer": "although", "category": "conjunction"},
    {"sentence": "I don't like tea, and ___ do I.", "answer": "neither", "category": "negative"},
    {"sentence": "By the time we arrived, the train ___.", "answer": "had left", "category": "past_perfect"},
    {"sentence": "There ___ a lot of people at the party.", "answer": "were", "category": "be_verb"},
    {"sentence": "She speaks English ___ than her brother.", "answer": "better", "category": "comparison"},
    {"sentence": "If I ___ you, I would take the job.", "answer": "were", "category": "conditional"},
    {"sentence": "He hasn't called me ___ last week.", "answer": "since", "category": "preposition"},
    {"sentence": "We stayed at a hotel ___ had a beautiful view.", "answer": "that", "category": "relative_pronoun"},
    {"sentence": "The book was so interesting that I couldn't ___ it down.", "answer": "put", "category": "phrasal_verb"},
    {"sentence": "You should not judge a book ___ its cover.", "answer": "by", "category": "preposition"},
    {"sentence": "I will call you when I ___ home.", "answer": "get", "category": "time_clause"},
    {"sentence": "She prefers coffee ___ tea.", "answer": "to", "category": "preference"},
    {"sentence": "The children ___ playing in the garden.", "answer": "are", "category": "present_continuous"},
    {"sentence": "I wish I ___ speak French fluently.", "answer": "could", "category": "wish"},
    {"sentence": "The meeting has been ___ until next week.", "answer": "postponed", "category": "passive"},
    {"sentence": "Either you or your brother ___ to help.", "answer": "has", "category": "either_or"},
    {"sentence": "She made me ___ for an hour.", "answer": "wait", "category": "causative"}
]

# Store current quiz globally
current_quiz: List[Dict] = []

def get_quiz(num_questions: int = 5, difficulty: str = "mixed") -> Dict:
    """Generate a new quiz with specified number of questions"""
    global current_quiz

    try:
        available_questions = questions_bank.copy()
        num_questions = min(num_questions, len(available_questions))
        current_quiz = random.sample(available_questions, num_questions)

        quiz_questions = []
        for i, question in enumerate(current_quiz):
            quiz_questions.append({
                "id": i,
                "sentence": question["sentence"],
                "category": question["category"],
                "number": i + 1
            })

        return {
            "success": True,
            "questions": quiz_questions,
            "total_questions": num_questions,
            "quiz_id": f"quiz_{random.randint(1000, 9999)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate quiz: {str(e)}"
        }

def submit_answers(answers: Union[List[str], Dict[str, str]]) -> Dict:
    """
    Evaluate submitted quiz answers

    Args:
        answers: List or Dictionary of user answers

    Returns:
        Dictionary containing score and detailed results
    """
    global current_quiz

    try:
        if not current_quiz:
            return {
                "success": False,
                "error": "No active quiz found. Please start a new quiz."
            }

        # Convert list to dict if needed
        if isinstance(answers, list):
            answers_dict = {str(i): ans for i, ans in enumerate(answers)}
        else:
            answers_dict = answers

        score = 0
        results = []

        for idx, question in enumerate(current_quiz):
            user_answer = answers_dict.get(str(idx), "").strip().lower()
            correct_answer = question["answer"].lower()
            is_correct = (user_answer == correct_answer)

            if is_correct:
                score += 1

            results.append({
                "question_number": idx + 1,
                "sentence": question["sentence"],
                "user_answer": user_answer or "(no answer)",
                "correct_answer": question["answer"],
                "correct": is_correct
            })

        total_questions = len(current_quiz)
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0

        return {
            "success": True,
            "score": score,
            "correct_count": score,
            "total": total_questions,
            "percentage": round(percentage, 1),
            "review": results
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to evaluate answers: {str(e)}"
        }
