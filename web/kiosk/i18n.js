// Kiosk screen text in English, Hindi and Kannada. Answers themselves are translated on the server.
export const LANGS = ["en", "hi", "kn"];
export const LOCALE = { en: "en-IN", hi: "hi-IN", kn: "kn-IN" };

const STRINGS = {
  en: {
    ready: "Ready", listening: "Listening", thinking: "Thinking", answering: "Answering", navigating: "Navigating",
    handover: "Reception", visitor_detected: "Visitor Detected", reconnecting: "Reconnecting",
    app_name: "Central Block Assistant", app_sub: "AI Campus Concierge",
    start_over: "Start over", start_over_title: "Start over for a new visitor",
    nav_chat: "Chat", nav_navigate: "Navigate", nav_courses: "Courses", nav_events: "Events", nav_contacts: "Contacts", nav_help: "Help",
    welcome_title: "Welcome to<br>CHRIST University", welcome_sub: "Your guide to the Central Block",
    welcome_lead: "I'm your campus assistant.<br>Where would you like to go?",
    mic_hint_off: "Tap the microphone to talk", mic_hint_on: "Listening. Tap the microphone again to stop.",
    mic_label_off: "Tap to speak", mic_label_on: "Listening… tap to stop",
    mic_aria_off: "Microphone off. Tap to speak", mic_aria_on: "Microphone on. Tap to turn it off",
    ask_label: "Type your question", ask_placeholder: "Type a question, or tap the mic to speak…", send: "Send",
    quick_actions: "Quick Actions",
    find_place: "Find a place", find_lead: "Pick a place, or ask me. Directions start from Reception on the Ground floor.",
    legend_you: "Your location", legend_route: "Route", legend_dest: "Destination", legend_lift: "Lift",
    legend_stairs: "Staircase", legend_wc: "Washroom",
    search_programme: "Search a programme…",
    events_title: "From the Academic Calendar", events_lead: "Key upcoming events at CHRIST University, Central Campus.",
    event_day: "Event day", multi_day: "Multi-day event", holiday: "Holiday",
    contacts_title: "Contacts", contacts_lead: "Key numbers, email addresses and links. Scan a code to save it on your phone.",
    help_title: "How to use this assistant", help_lead: "Speak, type, or tap. I only answer from verified Central Block information.",
    help_speak_h: "Speak", help_speak_p: "Choose your language, tap the microphone and ask your question. The microphone turns red while I listen. Tap it while I am talking to interrupt me.",
    help_type_h: "Type or tap", help_type_p: "Use the box at the bottom of Chat, or the buttons on each page.",
    help_dir_h: "Directions", help_dir_p: "Routes start at Reception on the Ground floor and show each floor you pass through.",
    help_person_h: "Need a person?", help_person_p: "Say \"talk to a person\". Anything I can't confirm goes to the reception desk.",
    help_privacy_h: "Your privacy", help_privacy_p: "The camera only notices that someone is in front of the kiosk. Faces are not recognised and no images or recordings are kept. Questions are logged without phone numbers or emails.",
    banner: "Someone else is being helped. I'll be with you in a moment.",
    noise_hint: "I only heard background noise. Tap the microphone and speak a little closer.",
    tile_find: "Find a Place", tile_courses: "Courses", tile_events: "Events", tile_timings: "Timings",
    tile_contacts: "Contacts", tile_person: "Talk to a Person",
    quick_dir: "Get Directions", quick_prog: "Programmes & Fees", quick_cal: "Academic Calendar", quick_contacts: "Important Contacts",
    offices: "Offices", library: "Library", closed_today: "Closed today", today_in_block: "Today in Central Block",
    open_now: "Open now", lunch_break: "Lunch break", closed_now: "Closed now", office_hours: "Office hours",
    central_library: "Central Block Library", hours: "Hours", mon_sat: "Mon – Sat", third_saturday: "Third Saturday",
    sunday: "Sunday", vacation: "Vacation", public_holidays: "Public holidays", closed: "Closed", same_as_week: "Same as Mon–Sat",
    today: "Today:", hours_unconfirmed: "These hours are not confirmed. Please check at reception.",
    view_on_map: "View on Map", scan_library: "Scan to open the library website",
    library_topic: "To {topic}, use the library website.", library_site: "Find everything about the library on its website.",
    library_timings: "Library timings", answer_source: "Where this answer comes from",
    check_reception: "Please check with the reception desk", reception_note: "Reception is on the Ground floor. You can also call or email:",
    route_health: "Show route to the Health Centre", all_contacts: "All contacts",
    show_route: "Show the route", see_programmes: "See the programmes", programme_details: "Programme details", open_calendar: "Open the calendar",
    route_to: "Route to {name}", your_destination: "your destination", start_reception: "Start: Reception", ground_floor: "Ground floor",
    destination: "Destination: {name}", floors_on_route: "Floors on this route:", ground: "Ground", basement: "Basement", floor_n: "Floor {n}",
    find_another: "Find another place", search_places: "Search rooms, offices, cafés…", no_place: "No place by that name. Try asking me instead.",
    all_departments: "All departments", in_block: "In Central Block", other_depts: "Other departments",
    count_campus: "Programmes offered at Central Campus: {n}", count_dept: "Programmes offered: {n}",
    not_in_block: "not in Central Block", not_in_block_cap: "Not in Central Block", level_all: "All",
    undergraduate: "Undergraduate", postgraduate: "Postgraduate", doctoral: "Doctoral",
    no_match: "No programmes match. Try another level or search.", none_selected: "No programme selected.",
    no_description: "No description has been published for this programme.", category: "Category", year_n: "Year {n}",
    registration_fee: "Registration fee: {fee}. Academic year {year}, as published.",
    view_details: "View Details", show_less: "Show less", fee_structure: "Fee Structure",
    unconfirmed_name: "This programme's name was missing in the source data and is unconfirmed.",
    holiday_prefix: "Holiday: {name}", nothing_month: "Nothing on the calendar this month.",
    calendar_missing: "The academic calendar doesn't cover this month yet.",
  },
  hi: {
    ready: "तैयार", listening: "सुन रहा हूँ", thinking: "सोच रहा हूँ", answering: "उत्तर दे रहा हूँ", navigating: "रास्ता दिखा रहा हूँ",
    handover: "रिसेप्शन", visitor_detected: "आगंतुक दिखे", reconnecting: "फिर से जुड़ रहा है",
    app_name: "सेंट्रल ब्लॉक सहायक", app_sub: "एआई कैंपस सहायक",
    start_over: "फिर से शुरू करें", start_over_title: "नए आगंतुक के लिए फिर से शुरू करें",
    nav_chat: "बातचीत", nav_navigate: "रास्ता", nav_courses: "पाठ्यक्रम", nav_events: "कार्यक्रम", nav_contacts: "संपर्क", nav_help: "सहायता",
    welcome_title: "क्राइस्ट यूनिवर्सिटी में<br>आपका स्वागत है", welcome_sub: "सेंट्रल ब्लॉक में आपका मार्गदर्शक",
    welcome_lead: "मैं आपका कैंपस सहायक हूँ।<br>आप कहाँ जाना चाहेंगे?",
    mic_hint_off: "बात करने के लिए माइक्रोफ़ोन दबाएँ", mic_hint_on: "सुन रहा हूँ। रोकने के लिए माइक्रोफ़ोन फिर से दबाएँ।",
    mic_label_off: "बोलने के लिए दबाएँ", mic_label_on: "सुन रहा हूँ… रोकने के लिए दबाएँ",
    mic_aria_off: "माइक्रोफ़ोन बंद है। बोलने के लिए दबाएँ", mic_aria_on: "माइक्रोफ़ोन चालू है। बंद करने के लिए दबाएँ",
    ask_label: "अपना प्रश्न लिखें", ask_placeholder: "प्रश्न लिखें, या बोलने के लिए माइक दबाएँ…", send: "भेजें",
    quick_actions: "त्वरित विकल्प",
    find_place: "जगह खोजें", find_lead: "कोई जगह चुनें, या मुझसे पूछें। रास्ता भूतल पर रिसेप्शन से शुरू होता है।",
    legend_you: "आपका स्थान", legend_route: "रास्ता", legend_dest: "गंतव्य", legend_lift: "लिफ्ट",
    legend_stairs: "सीढ़ियाँ", legend_wc: "शौचालय",
    search_programme: "कार्यक्रम खोजें…",
    events_title: "शैक्षणिक कैलेंडर से", events_lead: "क्राइस्ट यूनिवर्सिटी, सेंट्रल कैंपस के प्रमुख आगामी कार्यक्रम।",
    event_day: "कार्यक्रम का दिन", multi_day: "कई दिनों का कार्यक्रम", holiday: "अवकाश",
    contacts_title: "संपर्क", contacts_lead: "महत्वपूर्ण नंबर, ईमेल पते और लिंक। अपने फ़ोन में सहेजने के लिए कोड स्कैन करें।",
    help_title: "इस सहायक का उपयोग कैसे करें", help_lead: "बोलें, लिखें या दबाएँ। मैं केवल सत्यापित सेंट्रल ब्लॉक जानकारी से उत्तर देता हूँ।",
    help_speak_h: "बोलें", help_speak_p: "अपनी भाषा चुनें, माइक्रोफ़ोन दबाएँ और अपना प्रश्न पूछें। जब मैं सुनता हूँ तो माइक्रोफ़ोन लाल हो जाता है। मेरे बोलते समय इसे दबाकर आप मुझे रोक सकते हैं।",
    help_type_h: "लिखें या दबाएँ", help_type_p: "बातचीत के नीचे वाले बॉक्स या हर पेज के बटनों का उपयोग करें।",
    help_dir_h: "रास्ता", help_dir_p: "रास्ते भूतल पर रिसेप्शन से शुरू होते हैं और रास्ते की हर मंजिल दिखाते हैं।",
    help_person_h: "किसी व्यक्ति से बात करनी है?", help_person_p: "\"किसी व्यक्ति से बात करनी है\" कहें। जो मैं पक्का नहीं कर सकता, वह रिसेप्शन डेस्क को भेजा जाता है।",
    help_privacy_h: "आपकी गोपनीयता", help_privacy_p: "कैमरा केवल यह देखता है कि कियोस्क के सामने कोई है। चेहरे पहचाने नहीं जाते और कोई तस्वीर या रिकॉर्डिंग नहीं रखी जाती। प्रश्न फ़ोन नंबर या ईमेल के बिना दर्ज किए जाते हैं।",
    banner: "किसी और की मदद की जा रही है। मैं जल्द ही आपके पास आऊँगा।",
    noise_hint: "मुझे केवल पीछे का शोर सुनाई दिया। माइक्रोफ़ोन दबाएँ और थोड़ा पास आकर बोलें।",
    tile_find: "जगह खोजें", tile_courses: "पाठ्यक्रम", tile_events: "कार्यक्रम", tile_timings: "समय",
    tile_contacts: "संपर्क", tile_person: "किसी व्यक्ति से बात करें",
    quick_dir: "रास्ता पाएँ", quick_prog: "कार्यक्रम और फीस", quick_cal: "शैक्षणिक कैलेंडर", quick_contacts: "महत्वपूर्ण संपर्क",
    offices: "कार्यालय", library: "पुस्तकालय", closed_today: "आज बंद", today_in_block: "आज सेंट्रल ब्लॉक में",
    open_now: "अभी खुला है", lunch_break: "भोजन अवकाश", closed_now: "अभी बंद है", office_hours: "कार्यालय समय",
    central_library: "सेंट्रल ब्लॉक पुस्तकालय", hours: "समय", mon_sat: "सोम – शनि", third_saturday: "तीसरा शनिवार",
    sunday: "रविवार", vacation: "छुट्टियाँ", public_holidays: "सार्वजनिक अवकाश", closed: "बंद", same_as_week: "सोम–शनि जैसा",
    today: "आज:", hours_unconfirmed: "यह समय पुष्ट नहीं है। कृपया रिसेप्शन पर पूछें।",
    view_on_map: "नक्शे पर देखें", scan_library: "पुस्तकालय की वेबसाइट खोलने के लिए स्कैन करें",
    library_topic: "पुस्तकालय की पूरी जानकारी उसकी वेबसाइट पर है।", library_site: "पुस्तकालय की पूरी जानकारी उसकी वेबसाइट पर है।",
    library_timings: "पुस्तकालय का समय", answer_source: "यह उत्तर कहाँ से आया",
    check_reception: "कृपया रिसेप्शन डेस्क से पूछें", reception_note: "रिसेप्शन भूतल पर है। आप कॉल या ईमेल भी कर सकते हैं:",
    route_health: "हेल्थ सेंटर का रास्ता दिखाएँ", all_contacts: "सभी संपर्क",
    show_route: "रास्ता दिखाएँ", see_programmes: "कार्यक्रम देखें", programme_details: "कार्यक्रम का विवरण", open_calendar: "कैलेंडर खोलें",
    route_to: "{name} का रास्ता", your_destination: "आपका गंतव्य", start_reception: "शुरुआत: रिसेप्शन", ground_floor: "भूतल",
    destination: "गंतव्य: {name}", floors_on_route: "इस रास्ते की मंजिलें:", ground: "भूतल", basement: "तहखाना", floor_n: "मंजिल {n}",
    find_another: "दूसरी जगह खोजें", search_places: "कमरे, कार्यालय, कैफ़े खोजें…", no_place: "इस नाम की कोई जगह नहीं मिली। मुझसे पूछकर देखें।",
    all_departments: "सभी विभाग", in_block: "सेंट्रल ब्लॉक में", other_depts: "अन्य विभाग",
    count_campus: "सेंट्रल कैंपस में उपलब्ध कार्यक्रम: {n}", count_dept: "उपलब्ध कार्यक्रम: {n}",
    not_in_block: "सेंट्रल ब्लॉक में नहीं", not_in_block_cap: "सेंट्रल ब्लॉक में नहीं", level_all: "सभी",
    undergraduate: "स्नातक", postgraduate: "स्नातकोत्तर", doctoral: "डॉक्टरेट",
    no_match: "कोई कार्यक्रम नहीं मिला। दूसरा स्तर या खोज आज़माएँ।", none_selected: "कोई कार्यक्रम नहीं चुना गया।",
    no_description: "इस कार्यक्रम का विवरण प्रकाशित नहीं हुआ है।", category: "श्रेणी", year_n: "वर्ष {n}",
    registration_fee: "पंजीकरण शुल्क: {fee}। शैक्षणिक वर्ष {year}, प्रकाशित अनुसार।",
    view_details: "विवरण देखें", show_less: "कम दिखाएँ", fee_structure: "फीस संरचना",
    unconfirmed_name: "इस कार्यक्रम का नाम स्रोत डेटा में नहीं था और पुष्ट नहीं है।",
    holiday_prefix: "अवकाश: {name}", nothing_month: "इस महीने कैलेंडर में कुछ नहीं है।",
    calendar_missing: "शैक्षणिक कैलेंडर में अभी यह महीना शामिल नहीं है।",
  },
  kn: {
    ready: "ಸಿದ್ಧ", listening: "ಆಲಿಸುತ್ತಿದ್ದೇನೆ", thinking: "ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ", answering: "ಉತ್ತರಿಸುತ್ತಿದ್ದೇನೆ", navigating: "ದಾರಿ ತೋರಿಸುತ್ತಿದ್ದೇನೆ",
    handover: "ರಿಸೆಪ್ಷನ್", visitor_detected: "ಸಂದರ್ಶಕರು ಕಾಣಿಸಿದ್ದಾರೆ", reconnecting: "ಮರುಸಂಪರ್ಕಿಸುತ್ತಿದೆ",
    app_name: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್ ಸಹಾಯಕ", app_sub: "ಎಐ ಕ್ಯಾಂಪಸ್ ಮಾರ್ಗದರ್ಶಿ",
    start_over: "ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಿ", start_over_title: "ಹೊಸ ಸಂದರ್ಶಕರಿಗಾಗಿ ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಿ",
    nav_chat: "ಸಂಭಾಷಣೆ", nav_navigate: "ದಾರಿ", nav_courses: "ಕೋರ್ಸ್‌ಗಳು", nav_events: "ಕಾರ್ಯಕ್ರಮಗಳು", nav_contacts: "ಸಂಪರ್ಕಗಳು", nav_help: "ಸಹಾಯ",
    welcome_title: "ಕ್ರೈಸ್ಟ್ ಯೂನಿವರ್ಸಿಟಿಗೆ<br>ಸುಸ್ವಾಗತ", welcome_sub: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್‌ಗೆ ನಿಮ್ಮ ಮಾರ್ಗದರ್ಶಿ",
    welcome_lead: "ನಾನು ನಿಮ್ಮ ಕ್ಯಾಂಪಸ್ ಸಹಾಯಕ.<br>ನೀವು ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?",
    mic_hint_off: "ಮಾತನಾಡಲು ಮೈಕ್ರೊಫೋನ್ ಒತ್ತಿ", mic_hint_on: "ಆಲಿಸುತ್ತಿದ್ದೇನೆ. ನಿಲ್ಲಿಸಲು ಮೈಕ್ರೊಫೋನ್ ಅನ್ನು ಮತ್ತೆ ಒತ್ತಿ.",
    mic_label_off: "ಮಾತನಾಡಲು ಒತ್ತಿ", mic_label_on: "ಆಲಿಸುತ್ತಿದ್ದೇನೆ… ನಿಲ್ಲಿಸಲು ಒತ್ತಿ",
    mic_aria_off: "ಮೈಕ್ರೊಫೋನ್ ಆಫ್ ಆಗಿದೆ. ಮಾತನಾಡಲು ಒತ್ತಿ", mic_aria_on: "ಮೈಕ್ರೊಫೋನ್ ಆನ್ ಆಗಿದೆ. ಆಫ್ ಮಾಡಲು ಒತ್ತಿ",
    ask_label: "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ", ask_placeholder: "ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ, ಅಥವಾ ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ…", send: "ಕಳುಹಿಸಿ",
    quick_actions: "ತ್ವರಿತ ಆಯ್ಕೆಗಳು",
    find_place: "ಸ್ಥಳವನ್ನು ಹುಡುಕಿ", find_lead: "ಸ್ಥಳವನ್ನು ಆರಿಸಿ, ಅಥವಾ ನನ್ನನ್ನು ಕೇಳಿ. ದಾರಿ ನೆಲ ಮಹಡಿಯ ರಿಸೆಪ್ಷನ್‌ನಿಂದ ಪ್ರಾರಂಭವಾಗುತ್ತದೆ.",
    legend_you: "ನಿಮ್ಮ ಸ್ಥಳ", legend_route: "ಮಾರ್ಗ", legend_dest: "ಗಮ್ಯಸ್ಥಾನ", legend_lift: "ಲಿಫ್ಟ್",
    legend_stairs: "ಮೆಟ್ಟಿಲು", legend_wc: "ಶೌಚಾಲಯ",
    search_programme: "ಕೋರ್ಸ್ ಹುಡುಕಿ…",
    events_title: "ಶೈಕ್ಷಣಿಕ ಕ್ಯಾಲೆಂಡರ್‌ನಿಂದ", events_lead: "ಕ್ರೈಸ್ಟ್ ಯೂನಿವರ್ಸಿಟಿ, ಸೆಂಟ್ರಲ್ ಕ್ಯಾಂಪಸ್‌ನ ಮುಂಬರುವ ಪ್ರಮುಖ ಕಾರ್ಯಕ್ರಮಗಳು.",
    event_day: "ಕಾರ್ಯಕ್ರಮದ ದಿನ", multi_day: "ಹಲವು ದಿನಗಳ ಕಾರ್ಯಕ್ರಮ", holiday: "ರಜೆ",
    contacts_title: "ಸಂಪರ್ಕಗಳು", contacts_lead: "ಪ್ರಮುಖ ಸಂಖ್ಯೆಗಳು, ಇಮೇಲ್ ವಿಳಾಸಗಳು ಮತ್ತು ಲಿಂಕ್‌ಗಳು. ನಿಮ್ಮ ಫೋನ್‌ನಲ್ಲಿ ಉಳಿಸಲು ಕೋಡ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ.",
    help_title: "ಈ ಸಹಾಯಕವನ್ನು ಹೇಗೆ ಬಳಸುವುದು", help_lead: "ಮಾತನಾಡಿ, ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಒತ್ತಿ. ನಾನು ಪರಿಶೀಲಿಸಿದ ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್ ಮಾಹಿತಿಯಿಂದ ಮಾತ್ರ ಉತ್ತರಿಸುತ್ತೇನೆ.",
    help_speak_h: "ಮಾತನಾಡಿ", help_speak_p: "ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆರಿಸಿ, ಮೈಕ್ರೊಫೋನ್ ಒತ್ತಿ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿ. ನಾನು ಆಲಿಸುವಾಗ ಮೈಕ್ರೊಫೋನ್ ಕೆಂಪಾಗುತ್ತದೆ. ನಾನು ಮಾತನಾಡುವಾಗ ಅದನ್ನು ಒತ್ತಿ ನನ್ನನ್ನು ನಿಲ್ಲಿಸಬಹುದು.",
    help_type_h: "ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಒತ್ತಿ", help_type_p: "ಸಂಭಾಷಣೆಯ ಕೆಳಗಿನ ಪೆಟ್ಟಿಗೆ ಅಥವಾ ಪ್ರತಿ ಪುಟದ ಬಟನ್‌ಗಳನ್ನು ಬಳಸಿ.",
    help_dir_h: "ದಾರಿ", help_dir_p: "ಮಾರ್ಗಗಳು ನೆಲ ಮಹಡಿಯ ರಿಸೆಪ್ಷನ್‌ನಿಂದ ಪ್ರಾರಂಭವಾಗಿ ನೀವು ಹಾದುಹೋಗುವ ಪ್ರತಿ ಮಹಡಿಯನ್ನು ತೋರಿಸುತ್ತವೆ.",
    help_person_h: "ಯಾರೊಂದಿಗಾದರೂ ಮಾತನಾಡಬೇಕೆ?", help_person_p: "\"ವ್ಯಕ್ತಿಯೊಂದಿಗೆ ಮಾತನಾಡಬೇಕು\" ಎಂದು ಹೇಳಿ. ನಾನು ಖಚಿತಪಡಿಸಲಾಗದ ವಿಷಯಗಳನ್ನು ರಿಸೆಪ್ಷನ್‌ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ.",
    help_privacy_h: "ನಿಮ್ಮ ಗೌಪ್ಯತೆ", help_privacy_p: "ಕಿಯೋಸ್ಕ್ ಮುಂದೆ ಯಾರಾದರೂ ಇದ್ದಾರೆ ಎಂಬುದನ್ನು ಮಾತ್ರ ಕ್ಯಾಮೆರಾ ಗಮನಿಸುತ್ತದೆ. ಮುಖಗಳನ್ನು ಗುರುತಿಸುವುದಿಲ್ಲ ಮತ್ತು ಯಾವುದೇ ಚಿತ್ರ ಅಥವಾ ರೆಕಾರ್ಡಿಂಗ್ ಇಡುವುದಿಲ್ಲ. ಪ್ರಶ್ನೆಗಳನ್ನು ಫೋನ್ ಸಂಖ್ಯೆ ಅಥವಾ ಇಮೇಲ್ ಇಲ್ಲದೆ ದಾಖಲಿಸಲಾಗುತ್ತದೆ.",
    banner: "ಬೇರೊಬ್ಬರಿಗೆ ಸಹಾಯ ಮಾಡಲಾಗುತ್ತಿದೆ. ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ನಿಮ್ಮ ಬಳಿ ಬರುತ್ತೇನೆ.",
    noise_hint: "ನನಗೆ ಹಿನ್ನೆಲೆ ಶಬ್ದ ಮಾತ್ರ ಕೇಳಿಸಿತು. ಮೈಕ್ರೊಫೋನ್ ಒತ್ತಿ ಸ್ವಲ್ಪ ಹತ್ತಿರದಿಂದ ಮಾತನಾಡಿ.",
    tile_find: "ಸ್ಥಳ ಹುಡುಕಿ", tile_courses: "ಕೋರ್ಸ್‌ಗಳು", tile_events: "ಕಾರ್ಯಕ್ರಮಗಳು", tile_timings: "ಸಮಯ",
    tile_contacts: "ಸಂಪರ್ಕಗಳು", tile_person: "ವ್ಯಕ್ತಿಯೊಂದಿಗೆ ಮಾತನಾಡಿ",
    quick_dir: "ದಾರಿ ಪಡೆಯಿರಿ", quick_prog: "ಕೋರ್ಸ್‌ಗಳು ಮತ್ತು ಶುಲ್ಕ", quick_cal: "ಶೈಕ್ಷಣಿಕ ಕ್ಯಾಲೆಂಡರ್", quick_contacts: "ಪ್ರಮುಖ ಸಂಪರ್ಕಗಳು",
    offices: "ಕಚೇರಿಗಳು", library: "ಗ್ರಂಥಾಲಯ", closed_today: "ಇಂದು ಮುಚ್ಚಿದೆ", today_in_block: "ಇಂದು ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್‌ನಲ್ಲಿ",
    open_now: "ಈಗ ತೆರೆದಿದೆ", lunch_break: "ಊಟದ ವಿರಾಮ", closed_now: "ಈಗ ಮುಚ್ಚಿದೆ", office_hours: "ಕಚೇರಿ ಸಮಯ",
    central_library: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್ ಗ್ರಂಥಾಲಯ", hours: "ಸಮಯ", mon_sat: "ಸೋಮ – ಶನಿ", third_saturday: "ಮೂರನೇ ಶನಿವಾರ",
    sunday: "ಭಾನುವಾರ", vacation: "ರಜಾದಿನಗಳು", public_holidays: "ಸಾರ್ವಜನಿಕ ರಜೆಗಳು", closed: "ಮುಚ್ಚಿದೆ", same_as_week: "ಸೋಮ–ಶನಿಯಂತೆಯೇ",
    today: "ಇಂದು:", hours_unconfirmed: "ಈ ಸಮಯ ಖಚಿತವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ರಿಸೆಪ್ಷನ್‌ನಲ್ಲಿ ಕೇಳಿ.",
    view_on_map: "ನಕ್ಷೆಯಲ್ಲಿ ನೋಡಿ", scan_library: "ಗ್ರಂಥಾಲಯ ವೆಬ್‌ಸೈಟ್ ತೆರೆಯಲು ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
    library_topic: "ಗ್ರಂಥಾಲಯದ ಎಲ್ಲಾ ಮಾಹಿತಿ ಅದರ ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿದೆ.", library_site: "ಗ್ರಂಥಾಲಯದ ಎಲ್ಲಾ ಮಾಹಿತಿ ಅದರ ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿದೆ.",
    library_timings: "ಗ್ರಂಥಾಲಯದ ಸಮಯ", answer_source: "ಈ ಉತ್ತರದ ಮೂಲ",
    check_reception: "ದಯವಿಟ್ಟು ರಿಸೆಪ್ಷನ್ ಡೆಸ್ಕ್‌ನಲ್ಲಿ ಕೇಳಿ", reception_note: "ರಿಸೆಪ್ಷನ್ ನೆಲ ಮಹಡಿಯಲ್ಲಿದೆ. ನೀವು ಕರೆ ಅಥವಾ ಇಮೇಲ್ ಸಹ ಮಾಡಬಹುದು:",
    route_health: "ಆರೋಗ್ಯ ಕೇಂದ್ರಕ್ಕೆ ದಾರಿ ತೋರಿಸಿ", all_contacts: "ಎಲ್ಲಾ ಸಂಪರ್ಕಗಳು",
    show_route: "ದಾರಿ ತೋರಿಸಿ", see_programmes: "ಕೋರ್ಸ್‌ಗಳನ್ನು ನೋಡಿ", programme_details: "ಕೋರ್ಸ್ ವಿವರಗಳು", open_calendar: "ಕ್ಯಾಲೆಂಡರ್ ತೆರೆಯಿರಿ",
    route_to: "{name} – ದಾರಿ", your_destination: "ನಿಮ್ಮ ಗಮ್ಯಸ್ಥಾನ", start_reception: "ಪ್ರಾರಂಭ: ರಿಸೆಪ್ಷನ್", ground_floor: "ನೆಲ ಮಹಡಿ",
    destination: "ಗಮ್ಯಸ್ಥಾನ: {name}", floors_on_route: "ಈ ಮಾರ್ಗದ ಮಹಡಿಗಳು:", ground: "ನೆಲ", basement: "ನೆಲಮಾಳಿಗೆ", floor_n: "ಮಹಡಿ {n}",
    find_another: "ಬೇರೆ ಸ್ಥಳ ಹುಡುಕಿ", search_places: "ಕೊಠಡಿಗಳು, ಕಚೇರಿಗಳು, ಕೆಫೆಗಳನ್ನು ಹುಡುಕಿ…", no_place: "ಆ ಹೆಸರಿನ ಸ್ಥಳ ಇಲ್ಲ. ನನ್ನನ್ನು ಕೇಳಿ ನೋಡಿ.",
    all_departments: "ಎಲ್ಲಾ ವಿಭಾಗಗಳು", in_block: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್‌ನಲ್ಲಿ", other_depts: "ಇತರ ವಿಭಾಗಗಳು",
    count_campus: "ಸೆಂಟ್ರಲ್ ಕ್ಯಾಂಪಸ್‌ನಲ್ಲಿ ನೀಡುವ ಕೋರ್ಸ್‌ಗಳು: {n}", count_dept: "ನೀಡುವ ಕೋರ್ಸ್‌ಗಳು: {n}",
    not_in_block: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್‌ನಲ್ಲಿ ಇಲ್ಲ", not_in_block_cap: "ಸೆಂಟ್ರಲ್ ಬ್ಲಾಕ್‌ನಲ್ಲಿ ಇಲ್ಲ", level_all: "ಎಲ್ಲಾ",
    undergraduate: "ಪದವಿ", postgraduate: "ಸ್ನಾತಕೋತ್ತರ", doctoral: "ಡಾಕ್ಟರೇಟ್",
    no_match: "ಯಾವುದೇ ಕೋರ್ಸ್ ಹೊಂದುತ್ತಿಲ್ಲ. ಬೇರೆ ಹಂತ ಅಥವಾ ಹುಡುಕಾಟ ಪ್ರಯತ್ನಿಸಿ.", none_selected: "ಯಾವುದೇ ಕೋರ್ಸ್ ಆಯ್ಕೆಯಾಗಿಲ್ಲ.",
    no_description: "ಈ ಕೋರ್ಸ್‌ನ ವಿವರಣೆ ಪ್ರಕಟವಾಗಿಲ್ಲ.", category: "ವರ್ಗ", year_n: "ವರ್ಷ {n}",
    registration_fee: "ನೋಂದಣಿ ಶುಲ್ಕ: {fee}. ಶೈಕ್ಷಣಿಕ ವರ್ಷ {year}, ಪ್ರಕಟಿಸಿದಂತೆ.",
    view_details: "ವಿವರಗಳನ್ನು ನೋಡಿ", show_less: "ಕಡಿಮೆ ತೋರಿಸಿ", fee_structure: "ಶುಲ್ಕ ವಿವರ",
    unconfirmed_name: "ಈ ಕೋರ್ಸ್‌ನ ಹೆಸರು ಮೂಲ ಮಾಹಿತಿಯಲ್ಲಿ ಇರಲಿಲ್ಲ ಮತ್ತು ಖಚಿತವಾಗಿಲ್ಲ.",
    holiday_prefix: "ರಜೆ: {name}", nothing_month: "ಈ ತಿಂಗಳು ಕ್ಯಾಲೆಂಡರ್‌ನಲ್ಲಿ ಏನೂ ಇಲ್ಲ.",
    calendar_missing: "ಶೈಕ್ಷಣಿಕ ಕ್ಯಾಲೆಂಡರ್ ಇನ್ನೂ ಈ ತಿಂಗಳನ್ನು ಒಳಗೊಂಡಿಲ್ಲ.",
  },
};

let lang = "en";
export const getLang = () => lang;
export const locale = () => LOCALE[lang];

// Text for `key` in the current language (English if a translation is missing), with {placeholders} filled.
export function t(key, vars = {}) {
  const s = (STRINGS[lang] && STRINGS[lang][key]) ?? STRINGS.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
}

// Fill every element marked data-i18n / data-i18n-html / -placeholder / -aria / -title.
export function applyStatic(root = document) {
  document.documentElement.lang = lang;
  for (const n of root.querySelectorAll("[data-i18n]")) n.textContent = t(n.dataset.i18n);
  for (const n of root.querySelectorAll("[data-i18n-html]")) n.innerHTML = t(n.dataset.i18nHtml);
  for (const n of root.querySelectorAll("[data-i18n-placeholder]")) n.placeholder = t(n.dataset.i18nPlaceholder);
  for (const n of root.querySelectorAll("[data-i18n-aria]")) n.setAttribute("aria-label", t(n.dataset.i18nAria));
  for (const n of root.querySelectorAll("[data-i18n-title]")) n.title = t(n.dataset.i18nTitle);
  for (const b of root.querySelectorAll("button[data-lang]")) {
    b.classList.toggle("is-active", b.dataset.lang === lang);
    b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
  }
}

// Switch the screen language; returns true when it changed. Listeners get a "kiosk:lang" event.
export function setLang(next) {
  const value = LANGS.includes(next) ? next : "en";
  const changed = value !== lang;
  lang = value;
  document.body.dataset.lang = lang;
  applyStatic();
  if (changed) window.dispatchEvent(new CustomEvent("kiosk:lang", { detail: { lang } }));
  return changed;
}
