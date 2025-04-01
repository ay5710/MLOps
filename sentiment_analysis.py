import ast
import openai
import os

from dotenv import load_dotenv
from openai import OpenAI


class Sentimentalization:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI()
    
    def get_sentiment(self, review):     
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
            print(f"API call failed for review: {e}")
            return None
            
        answer = completion.choices[0].message.content
        return answer