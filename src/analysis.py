import ast
import openai
import os

from dotenv import load_dotenv
from openai import OpenAI
from src.utils.logger import get_backend_logger

logger = get_backend_logger()


class GPT:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI()

    def sentiment(self, review, movie_id):
        text = review[3] + f"\n\n" + review[4]

        prompt = f"""
Instructions:
Below is a movie review that I want you to analyze.
For each of the following aspect, you must determine if it is mentioned in the review, and if it is, what is the corresponding sentiment on the following scale: *very negative*, *negative*, *neutral* (including mixed or contradictory sentiments), *positive*, *very positive*.
- *Storytelling* (including characters and their development, narrative progression, plot twists, screenplay, dialogues, overall pacing)
- *Acting performance* (including vocal, musical, danse, or stunt work if applicable)
- *Cinematography and visual style* (including colors and lightening, set design, costumes, makeup, special effects, overall aesthetic of the film)
- *Music and sound design* (including soundtrack and scores)
- *Theme and values* (including the moral or political message, emotional resonance, cultural or societal impact)
Your answer should take the form of a Python list with each aspect, whether it is mentioned, and the corresponding sentiment (which should be 'NA' if the aspect is not mentioned).
Additionally, I want you to identify the overall sentiment about the movie that the review conveys: is the movie *excellent*, *good despite minor flaws*, *average*, *bad despite some qualities*, *terrible*. This overall sentiment should be appended to the previous list.
You must return this list only, without any additional commentary. Your answer should have the following format (with example values):
 [('Storytelling', 'not mentioned', 'NA'), ('Acting performance', 'mentioned', 'good'), ('Cinematography and visual style', 'mentioned', 'very negative'), ('Music and sound design', 'mentioned', 'very good'), ('Theme and values', 'not mentioned', 'NA'), ('Overall', 'average')]

Now the review:
{text}
"""

        try:
            completion = self.client.chat.completions.create(
                model = "gpt-4o-mini",
                messages = [{"role": "user", "content": prompt}]
            )
        except Exception as e:
            logger.info(f"{movie_id} - API call failed for review by {review[2]}: {e}")
            return None

        # Extract list from API answer
        try:
            raw_answer = completion.choices[0].message.content
            answer = ast.literal_eval(raw_answer)
        except Exception:
            # GPT may stray from its intended behavior in at least 2 ways:
            try:
                # Replace fancy quotes signs
                clean_answer = raw_answer.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
                answer = ast.literal_eval(clean_answer)
            except Exception:
                try:
                    # Remove python markup
                    clean_answer = raw_answer.replace("```python", "").replace("```", "")
                    answer = ast.literal_eval(clean_answer)
                except Exception:
                    logger.error(f"{movie_id} - Failed to parse GPT answer for review by {review[2]}")
                    logger.error(f"{movie_id} - GPT answer: {raw_answer}")
                    return None

        # Convert categories into integers
        sentiment_mapping = {
            'very negative': -2,
            'negative': -1,
            'neutral': 0,
            'positive': 1,
            'very positive': 2,
            'terrible': -2,
            'bad despite some qualities': -1,
            'average': 0,
            'good despite minor flaws': 1,
            'excellent': 2,
            'NA': None}
        mapped_values = [None] * 6

        # Map aspect-based sentiments
        try:
            for i, (label, _, sentiment) in enumerate(answer[:5]):
                if sentiment in sentiment_mapping:
                    mapped_values[i] = sentiment_mapping[sentiment]
        except Exception as e:
            logger.error(f"{movie_id} - Failed to map aspect-based sentiments for review by {review[2]}: {e}")
            return None

        # Map overall sentiment
        try:
            label, sentiment = answer[5]
            if sentiment in sentiment_mapping:
                mapped_values[5] = sentiment_mapping[sentiment]
        except Exception as e:
            logger.error(f"{movie_id} - Failed to map overall sentiment for review by {review[2]}: {e}")
            return None

        return mapped_values
