def get_response(message):
    message = message.lower()

    if message in ["hi", "hello"]:
        return (
            "Hello 👋\n"
            "I’m A.M. Yusuf — Biochemist, Innovator, Bible Teacher, and Entrepreneur.\n\n"
            "Type *menu* to continue."
        )

    if message == "menu":
        return (
            "What would you like to explore?\n"
            "1️⃣ Research & Innovation\n"
            "2️⃣ AI & Digital Skills\n"
            "3️⃣ Consulting\n"
            "4️⃣ Faith & Leadership"
        )

    if message == "1":
        return "My research focuses on biochemistry, AI in healthcare, precision medicine, and agriculture."
    if message == "2":
        return "I train people to monetize AI and digital skills with practical execution."
    if message == "3":
        return "I consult for startups, strategy, and tech adoption."
    if message == "4":
        return "I teach biblical principles for leadership, purpose, and growth."

    return "Please type *menu* to continue."
