export type Language = "en" | "mr";

// Centralized UI string dictionary — backend identifiers, API fields and
// database values are never translated here; this covers on-screen
// copy only. Scoped to the citizen-facing screens the product spec
// calls out (nav, home, journey, vault, consent, status/next-action,
// common errors), not an exhaustive translation of every string.
export const translations = {
  nav_home: { en: "Home", mr: "मुख्यपृष्ठ" },
  nav_services: { en: "Discover Services", mr: "सेवा शोधा" },
  nav_journeys: { en: "My Journeys", mr: "माझे प्रवास" },
  nav_vault: { en: "Documents", mr: "कागदपत्रे" },
  nav_profile: { en: "Profile", mr: "प्रोफाइल" },
  nav_demo: { en: "Judge Demo", mr: "परीक्षक डेमो" },
  nav_admin: { en: "Admin", mr: "प्रशासन" },

  home_tagline: {
    en: "Citizens shouldn't have to know which department provides a service. Tell SETU what you need — it discovers the required government services, reuses what's already verified, and coordinates the rest.",
    mr: "नागरिकांना कोणता विभाग सेवा पुरवतो हे कळण्याची गरज नाही. SETU ला तुम्हाला काय हवे आहे ते सांगा — ते आवश्यक शासकीय सेवा शोधते, आधीच पडताळणी केलेले पुन्हा वापरते आणि उर्वरित समन्वय साधते.",
  },
  home_how_it_works: { en: "How SETU works", mr: "SETU कसे कार्य करते" },
  home_tell_us: { en: "Tell us what you need", mr: "तुम्हाला काय हवे ते सांगा" },
  home_start_journey: { en: "Start this journey", mr: "हा प्रवास सुरू करा" },
  home_coming_soon: { en: "Coming soon", mr: "लवकरच" },
  home_central_message: {
    en: "SETU does not replace existing government portals. It connects them around the citizen's goal.",
    mr: "SETU विद्यमान शासकीय पोर्टल्सची जागा घेत नाही. ते नागरिकांच्या उद्दिष्टाभोवती त्यांना जोडते.",
  },

  status_not_started: { en: "Not started", mr: "सुरू नाही" },
  status_blocked: { en: "Blocked", mr: "अडथळा" },
  status_in_progress: { en: "In progress", mr: "प्रगतीपथावर" },
  status_verified: { en: "Verified", mr: "पडताळणी झाली" },
  status_ready: { en: "Ready", mr: "तयार" },
  status_rejected: { en: "Rejected", mr: "नाकारले" },

  doc_status_uploaded: { en: "Uploaded", mr: "अपलोड केले" },
  doc_status_under_review: { en: "Under review", mr: "पुनरावलोकनाधीन" },
  doc_status_verified: { en: "Verified", mr: "पडताळणी झाली" },
  doc_status_rejected: { en: "Rejected", mr: "नाकारले" },
  doc_status_expired: { en: "Expired", mr: "मुदत संपली" },

  action_reset_demo: { en: "Reset demo", mr: "डेमो रीसेट करा" },
  action_grant_consent: { en: "Grant consent", mr: "संमती द्या" },
  action_revoke_consent: { en: "Revoke consent", mr: "संमती मागे घ्या" },
  action_submit: { en: "Submit", mr: "सादर करा" },
  action_approve: { en: "Simulate approval", mr: "मंजुरीचे अनुकरण करा" },
  action_submit_for_review: { en: "Submit for review", mr: "पुनरावलोकनासाठी सादर करा" },
  action_verify: { en: "Verify", mr: "पडताळणी करा" },
  action_reject: { en: "Reject", mr: "नाकारा" },
  action_upload: { en: "Upload document", mr: "कागदपत्र अपलोड करा" },
  action_start_journey: { en: "Start journey", mr: "प्रवास सुरू करा" },

  journey_current_blocker: { en: "Current blocker", mr: "सध्याचा अडथळा" },
  journey_next_action: { en: "Next action", mr: "पुढील कृती" },
  journey_timeline: { en: "Unified journey timeline", mr: "एकीकृत प्रवास टाइमलाइन" },
  journey_none: { en: "None — nothing is blocking this journey.", mr: "काहीही नाही — या प्रवासात कोणताही अडथळा नाही." },

  consent_title: { en: "Consent", mr: "संमती" },
  consent_explain: {
    en: "Before any data is shared, you control exactly what, with whom, and why.",
    mr: "कोणताही डेटा शेअर करण्यापूर्वी, काय, कोणासोबत आणि का हे तुम्ही नियंत्रित करता.",
  },

  error_generic: { en: "Something went wrong. Please try again.", mr: "काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा." },
  loading: { en: "Loading…", mr: "लोड होत आहे…" },
} as const;

export type TranslationKey = keyof typeof translations;
