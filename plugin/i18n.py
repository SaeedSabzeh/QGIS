"""User-interface strings in Italian and English; the panel shows one language at a time.

The language comes from the plugin setting "ui_language" ("auto", "it" or "en"). With "auto"
it follows the QGIS user locale (Italian when it starts with "it", English otherwise).
"""

STRINGS = {
    'idle': (
        'Attiva lo strumento e fai clic su un punto di Milano.',
        'Turn on the tool and click a point in Milan.'),
    'querying': (
        'Ricerca delle norme in corso…',
        'Looking up the rules…'),
    'point': (
        'Punto: %.5f, %.5f',
        'Point: %.5f, %.5f'),
    'all_failed': (
        'Nessun servizio cartografico ha risposto. Controlla la connessione e le impostazioni del proxy.',
        'No map service answered. Check the connection and proxy settings.'),
    'some_failed': (
        '%d di %d livelli non disponibili.',
        '%d of %d layers unavailable.'),
    'query_failed': (
        'Ricerca non riuscita: %s',
        'Lookup failed: %s'),
    'ask_failed': (
        'La richiesta al modello non è riuscita: %s. Vincoli e articoli restano disponibili.',
        'The model request failed: %s. The constraints and articles are still available.'),
    'click_first': (
        'Fai prima clic su un punto di Milano.',
        'Click a point in Milan first.'),
    'sec_constraints': (
        'Vincoli nel punto selezionato',
        'Constraints at the selected point'),
    'sec_articles': (
        'Articoli',
        'Articles'),
    'sec_question': (
        'Domanda',
        'Question'),
    'no_constraints': (
        'Nessun vincolo e nessuna zona individuati nel punto selezionato.',
        'No planning constraint or zone found at this point.'),
    'governing': (
        'Articoli di riferimento',
        'Governing articles'),
    'general': (
        'Generali',
        'General'),
    'explanatory': (
        'Illustrativi',
        'Explanatory'),
    'candidate': (
        'Da verificare',
        'To check'),
    'verify': (
        'Da verificare',
        'To verify'),
    'verify_note': (
        'Collegamento tra vincolo e articolo da verificare: non ancora confermato da un revisore.',
        'The link between this constraint and the article still needs checking by a reviewer.'),
    'external': (
        'Norma esterna ai testi del PGT',
        'Rule outside the PGT texts'),
    'unverified': (
        'non verificata',
        'unverified'),
    'official_map': (
        'Livello cartografico ufficiale',
        'Official map layer'),
    'official_park': (
        'Piano del parco',
        'Park plan'),
    'layer_errors': (
        'Livelli non disponibili',
        'Unavailable layers'),
    'why': (
        'Perché',
        'Why'),
    'fam_zoning': (
        'Zona del PGT',
        'PGT zone'),
    'fam_landscape': (
        'Paesaggio',
        'Landscape'),
    'fam_geology': (
        'Geologia',
        'Geology'),
    'fam_flood': (
        'Rischio di alluvioni',
        'Flood risk'),
    'fam_nature': (
        'Parchi e natura',
        'Parks and nature'),
    'no_articles': (
        'Nessun articolo collegato.',
        'No linked articles.'),
    'role_governing': (
        'articolo di riferimento',
        'governing article'),
    'role_general': (
        'articolo di carattere generale',
        'general article'),
    'role_candidate': (
        'da verificare',
        'to check'),
    'role_explanatory': (
        'illustrativo, non normativo',
        'explanatory, non-normative'),
    'role_cited': (
        'citato nella risposta',
        'cited in the answer'),
    'open_publication': (
        'Apri pubblicazione ufficiale',
        'Open the official publication'),
    'pages': (
        'pp. %s del PDF',
        'PDF pp. %s'),
    'placeholder': (
        'Fai una domanda sulle norme nel punto selezionato…',
        'Ask about the rules at this point…'),
    'ask': (
        'Chiedi',
        'Ask'),
    'settings': (
        'Impostazioni',
        'Settings'),
    'no_provider': (
        "Per fare domande, configura l'IA nelle <a href='settings'>Impostazioni</a>.",
        "To ask questions, set up the AI in <a href='settings'>Settings</a>."),
    'asking': (
        'Elaborazione della risposta in corso…',
        'Preparing the answer…'),
    'answer': (
        'Risposta',
        'Answer'),
    'answered_by': (
        'Risposta di %s · articoli citati: %s',
        'Answered by %s · cited articles: %s'),
    'none': (
        'nessuno',
        'none'),
    'check_sources': (
        'Verifica le fonti: alcune citazioni non sono state confermate.',
        'Check the sources: some citations could not be confirmed.'),
    'passages': (
        'Estratti degli articoli',
        'Article extracts'),
    'rejected': (
        'Il modello ha citato articoli non inclusi nei testi forniti. I relativi riferimenti sono stati rimossi: %s',
        'The model cited articles that were not among the supplied texts. Those references were removed: %s'),
    'parse_error': (
        'Non è stato possibile interpretare la risposta del modello.',
        'The model reply could not be interpreted.'),
    'outside_title': (
        'Fuori dal territorio del Comune di Milano',
        'Outside the Comune di Milano'),
    'footer': (
        "Le informazioni hanno carattere orientativo e non costituiscono un parere legale. <a href='details'>Dettagli</a>",
        "Guidance only, not legal advice. <a href='details'>Details</a>"),
    'footer_hide': (
        "Le informazioni hanno carattere orientativo e non costituiscono un parere legale. <a href='details'>Nascondi</a>",
        "Guidance only, not legal advice. <a href='details'>Hide</a>"),
    'docs_used': (
        'Documenti consultati: %s.',
        'Documents used: %s.'),
    'set_title': (
        'Norme Milano – Impostazioni',
        'Norme Milano – Settings'),
    'set_welcome': (
        "<b>Benvenuto.</b> Il plugin mostra vincoli e articoli anche senza configurare l'IA. Per fare domande, scegli Gemini o Ollama.",
        '<b>Welcome.</b> Without a model the plugin shows the constraints and articles. To ask questions, choose Gemini or Ollama.'),
    'set_language': (
        'Lingua',
        'Language'),
    'set_lang_auto': (
        'Automatica (lingua di QGIS)',
        'Automatic (as QGIS)'),
    'set_provider': (
        'Servizio IA per le domande',
        'AI service for questions'),
    'prov_none': (
        'Nessuno (solo vincoli e articoli)',
        'None (constraints and articles only)'),
    'prov_gemini': (
        'Gemini (Google)',
        'Gemini (Google)'),
    'prov_ollama': (
        'Ollama',
        'Ollama'),
    'set_gemini_model': (
        'Modello Gemini',
        'Gemini model'),
    'set_gemini_key': (
        'Chiave API Gemini',
        'Gemini API key'),
    'set_key_link': (
        'Crea una chiave API Gemini (Google AI Studio)',
        'Create a Gemini API key (Google AI Studio)'),
    'set_remove_key': (
        'Rimuovi',
        'Remove'),
    'set_key_removed': (
        'Chiave API rimossa.',
        'API key removed.'),
    'set_ollama_url': (
        'Indirizzo del server Ollama',
        'Ollama server address'),
    'set_ollama_model': (
        'Modello Ollama',
        'Ollama model'),
    'set_test': (
        'Verifica connessione',
        'Test connection'),
    'set_testing': (
        'Verifica in corso…',
        'Testing…'),
    'set_test_ok': (
        'OK: %s',
        'OK: %s'),
    'set_test_failed': (
        'Verifica non riuscita: %s',
        'Failed: %s'),
    'key_stored': (
        'Chiave salvata (lascia il campo vuoto per mantenerla)',
        'Key stored (leave the field empty to keep it)'),
    'key_paste': (
        'Incolla la tua chiave API Gemini',
        'Paste your Gemini API key'),
    'privacy_gemini': (
        'Privacy: domanda, vincoli e testi degli articoli vengono inviati a Google. Nel piano gratuito Google può usarli per migliorare i suoi prodotti.',
        'Privacy: the question, constraints and article texts are sent to Google. On the free tier Google may use them to improve its products.'),
    'privacy_ollama': (
        'Privacy: domanda, vincoli e testi degli articoli vengono inviati al server Ollama configurato (per impostazione predefinita sul tuo computer).',
        'Privacy: the question, constraints and article texts are sent to the configured Ollama server (your computer by default).'),
    'privacy_none': (
        'Privacy: ai servizi cartografici pubblici vengono inviate solo le coordinate del punto.',
        "Privacy: only the point's coordinates are sent to the public map services."),
    'note_plain': (
        'Chiave salvata senza cifratura nelle impostazioni del profilo QGIS. Per proteggerla con la cifratura, imposta una password principale in Opzioni > Autenticazione.',
        'Stored in your QGIS profile settings (not encrypted). To encrypt it, set a QGIS master password in Options > Authentication.'),
    'note_auth': (
        "Chiave salvata con cifratura nell'archivio di autenticazione di QGIS.",
        'Stored encrypted in the QGIS password store.'),
    'note_env': (
        "Chiave letta dalla variabile d'ambiente %s.",
        'Using %s from the environment.'),
    'note_none_auth': (
        "La chiave verrà salvata con cifratura nell'archivio di autenticazione di QGIS.",
        'Will be stored encrypted in the QGIS password store.'),
    'note_reenter': (
        "Non è stato possibile leggere la chiave API Gemini salvata: l'archivio di autenticazione di QGIS è bloccato o non disponibile. Inseriscila di nuovo.",
        'The stored Gemini key could not be read (the QGIS password store is locked or unavailable). Enter it again.'),
    'summary': (
        '%d vincoli:',
        '%d constraints:'),
    'more': (
        'Mostra di più',
        'Show more'),
    'less': (
        'Mostra di meno',
        'Show less'),
    'why_en_only': (
        'Motivazione tecnica (solo in inglese)',
        'Technical reasoning'),
    'grp_governing': (
        'Articoli di riferimento',
        'Governing articles'),
    'grp_general': (
        'Altri articoli collegati',
        'Other related articles'),
    'copy': (
        'Copia',
        'Copy'),
    'copied': (
        'Risposta copiata',
        'Answer copied'),
    'ea_strip': (
        "Pro è in arrivo: verifica dell'intero lotto, report PDF con le fonti, domande senza chiave API.",
        'Pro is in the works: whole-parcel check, PDF report with sources, questions without an API key.'),
    'ea_link': (
        "Richiedi l'accesso anticipato gratuito",
        'Get free early access'),
    'ea_tip': (
        'Apre la pagina di iscrizione nel browser. Il plugin non raccoglie il tuo indirizzo email.',
        'Opens the sign-up page in your browser. The plugin does not collect your email.'),
    'ea_close_tip': (
        'Non mostrare più',
        "Don't show again"),
    'ea_settings': (
        'Norme Milano Pro (in arrivo): accesso anticipato',
        'Norme Milano Pro (coming): early access'),
    'ea_tip_mail': (
        "Apre il tuo programma di posta con un breve messaggio già compilato e indirizzato a %s. "
        "Decidi tu se inviarlo; il plugin non invia nulla.",
        "Opens your email app with a short message already written and addressed to %s. "
        "You decide whether to send it; the plugin sends nothing."),
    'ea_mail_subject': (
        "Norme Milano Pro: accesso anticipato",
        "Norme Milano Pro: early access"),
    'ea_mail_body': (
        "Buongiorno,\n\nvorrei richiedere l'accesso anticipato gratuito a Norme Milano Pro.\n\n"
        "Il mio ruolo (architetto, geometra, urbanista, altro): \n"
        "Per un report su un lotto al prezzo di 29 €, la mia risposta sarebbe (lo comprerei subito / "
        "forse più avanti / uso solo strumenti gratuiti / non so): \n\n"
        "(Nota dell'autore di Norme Milano: userò il tuo indirizzo email solo per risponderti in "
        "merito a Pro. Puoi scrivermi in qualsiasi momento per chiederne la cancellazione.)",
        "Hello,\n\nI'd like to request free early access to Norme Milano Pro.\n\n"
        "My role (architect, geometra, planner, other): \n"
        "For a parcel report at €29, my answer would be (buy one now / maybe later / "
        "I only use free tools / not sure): \n\n"
        "(Note from the author of Norme Milano: I'll use your email address only to reply about "
        "Pro. You can write to me at any time to have it deleted.)"),
    'ea_mail_failed': (
        "Impossibile aprire il programma di posta. Scrivi a %s per l'accesso anticipato.",
        "Your email app could not be opened. Write to %s for early access."),
    'ea_open_failed': (
        'Impossibile aprire il browser. Pagina di iscrizione: %s',
        'The browser could not be opened. Sign-up page: %s'),
    'fallback_note': (
        'Risposta di un modello di riserva: verificala con attenzione.',
        'Answered by a fallback model: check it carefully.'),
}


def resolve(setting):
    """"it" or "en" for a ui_language setting value ("auto", "it", "en")."""
    if setting in ("it", "en"):
        return setting
    try:
        from qgis.core import QgsSettings
        locale = str(QgsSettings().value("locale/userLocale", "") or "")
        if not locale:
            from qgis.PyQt.QtCore import QLocale
            locale = str(QLocale.system().name())
    except Exception:  # no QGIS (tests) or an unusual locale object
        locale = ""
    return "it" if locale.lower().startswith("it") else "en"


def text(key, lang):
    """The string for `key` in `lang` ("it" or "en")."""
    it, en = STRINGS[key]
    return it if lang == "it" else en
