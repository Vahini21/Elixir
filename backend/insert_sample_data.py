import sqlite3
import os

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "elixir_healthcare.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert sample portfolio data for person1@gmail.com
sample_data = {
    'user_email': 'person1@gmail.com',
    'initials': 'JD',
    'age': '35',
    'gender': 'male',
    'insurance': 'BlueCross BlueShield - Policy #BC123456',
    'living': 'Living with spouse and 2 children',
    'drug_allergies': 'Penicillin - causes rash and hives',
    'env_allergies': 'Pollen, dust mites - seasonal allergies with sneezing',
    'adr': 'Ibuprofen - stomach upset',
    'chief_complaint': 'Annual physical examination and routine health checkup',
    'history_illness': 'Generally healthy, no current symptoms. Last physical was 1 year ago.',
    'past_medical': 'Hypertension (controlled with medication), Appendectomy (2015)',
    'family_history': 'Father: Type 2 Diabetes, Heart Disease. Mother: Hypertension. Maternal grandmother: Breast cancer.',
    'tobacco': 1,
    'tobacco_details': 'Previous smoker - quit 5 years ago. Used to smoke 1 pack/day for 10 years.',
    'alcohol': 0,
    'alcohol_details': '',
    'caffeine': 1,
    'caffeine_details': '3-4 cups of coffee per day',
    'recreation': 0,
    'recreation_details': '',
    'immunization_comments': 'Up to date on all vaccinations. Last flu shot: October 2024. COVID-19 boosters: Current.',
    'medications': 'Lisinopril 10mg daily (for hypertension), Vitamin D3 1000 IU daily, Multivitamin daily',
    'antibiotics': 'Amoxicillin taken for 7 days in September 2024 for sinus infection'
}

cursor.execute("""
    INSERT OR REPLACE INTO portfolio (
        user_email, initials, age, gender, insurance, living,
        drug_allergies, env_allergies, adr,
        chief_complaint, history_illness, past_medical, family_history,
        tobacco, tobacco_details, alcohol, alcohol_details,
        caffeine, caffeine_details, recreation, recreation_details,
        immunization_comments, medications, antibiotics
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    sample_data['user_email'],
    sample_data['initials'],
    sample_data['age'],
    sample_data['gender'],
    sample_data['insurance'],
    sample_data['living'],
    sample_data['drug_allergies'],
    sample_data['env_allergies'],
    sample_data['adr'],
    sample_data['chief_complaint'],
    sample_data['history_illness'],
    sample_data['past_medical'],
    sample_data['family_history'],
    sample_data['tobacco'],
    sample_data['tobacco_details'],
    sample_data['alcohol'],
    sample_data['alcohol_details'],
    sample_data['caffeine'],
    sample_data['caffeine_details'],
    sample_data['recreation'],
    sample_data['recreation_details'],
    sample_data['immunization_comments'],
    sample_data['medications'],
    sample_data['antibiotics']
))

conn.commit()
conn.close()

print("Sample portfolio data inserted successfully for person1@gmail.com!")
print("\nSample data includes:")
print("- Patient Initials: JD")
print("- Age: 35")
print("- Gender: Male")
print("- Insurance: BlueCross BlueShield")
print("- Allergies: Penicillin, Pollen, Ibuprofen")
print("- Medical History: Hypertension, Appendectomy")
print("- Family History: Diabetes, Heart Disease, Hypertension, Breast Cancer")
print("- Social History: Previous smoker, Caffeine user")
print("- Medications: Lisinopril, Vitamins")
print("\nYou can now log in as person1@gmail.com / 123 to see the filled form!")