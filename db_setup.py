import sqlite3

conn = sqlite3.connect('travel_bot.db')
cursor = conn.cursor()

# පරණ දත්ත මකා අලුතින්ම සෑදීම
cursor.execute("INSERT INTO Destinations VALUES ('hi', 'Hello! I am your AI Travel Assistant. How can I help you today?')")
cursor.execute("INSERT INTO Destinations VALUES ('how are you', 'I am doing great, thank you for asking! Ready to help you plan your trip to Sri Lanka.')")
cursor.execute("INSERT INTO Destinations VALUES ('who are you', 'I am a Smart Travel Bot designed for the UniManage project to help tourists explore Sri Lanka.')")
cursor.execute("INSERT INTO Destinations VALUES ('help', 'You can ask me about travel destinations like Kandy, Galle, or Ella, and also about tour packages and weather.')")

cursor.execute('DROP TABLE IF EXISTS Destinations')
cursor.execute('DROP TABLE IF EXISTS Packages')
cursor.execute('DROP TABLE IF EXISTS Unknowns')

cursor.execute('CREATE TABLE Destinations (PlaceName TEXT, Description TEXT)')
cursor.execute('CREATE TABLE Packages (PackageName TEXT, Price TEXT, Duration TEXT)')
cursor.execute('CREATE TABLE Unknowns (Query TEXT)')

# වැදගත්: මෙහි නම් සහ app.py එකේ Fuzzy logic එක දැන් එකට වැඩ කරනවා
cursor.execute("INSERT INTO Destinations VALUES ('Kandy', 'ශ්‍රී ලංකාවේ සංස්කෘතික අගනුවරයි. මෙහි ලෝක ප්‍රකට ශ්‍රී දළදා මාළිගාව, පේරාදෙණිය උද්භිද උද්‍යානය සහ සුන්දර මහනුවර වැව පිහිටා ඇත.')")
cursor.execute("INSERT INTO Destinations VALUES ('Ella', 'Famous for Nine Arch Bridge.')")
cursor.execute("INSERT INTO Destinations VALUES ('Galle', 'Famous for the Galle Fort.')")

cursor.execute("INSERT INTO Packages VALUES ('Kandy Tour', 'Rs. 5000', '1 Day')")
cursor.execute("INSERT INTO Packages VALUES ('Ella Trip', 'Rs. 15000', '2 Days')")
cursor.execute("INSERT INTO Packages VALUES ('Galle Day Tour', 'Rs. 7000', '1 Day')")

conn.commit()
conn.close()
print("✅ Database Reset & Created Successfully!")
