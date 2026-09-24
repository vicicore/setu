-- Demo/mock catalog data — no PII. Services + life events used across all
-- demo journeys (signature: College Admission + Scholarship; secondary:
-- Starting a Small Business).

insert into services (code, name, department, sla_days, description) values
  ('domicile_certificate', 'Domicile Certificate', 'Revenue', 7, 'Proof of residence in Maharashtra'),
  ('income_certificate', 'Income Certificate', 'Revenue', 10, 'Proof of annual family income'),
  ('caste_certificate', 'Caste Certificate', 'Social Justice', 15, 'Caste validity/eligibility document'),
  ('education_scholarship', 'Engineering Admission Scholarship', 'Higher Education', 21, 'Scholarship for engineering admission'),
  ('identity_verification', 'Identity Verification', 'Home', 1, 'Aadhaar/DigiLocker-backed identity check'),
  ('business_registration', 'Shop & Establishment Registration', 'Labour', 10, 'Registers a small business/shop'),
  ('local_noc', 'Local Body NOC', 'Urban Development', 14, 'No-objection certificate from the local municipal body'),
  ('gst_registration', 'GST Registration', 'Finance', 7, 'Tax registration for a new business')
on conflict (code) do nothing;

insert into life_events (code, title_en, title_mr, title_hi, description) values
  ('college_admission_scholarship', 'College Admission + Scholarship',
   'महाविद्यालय प्रवेश + शिष्यवृत्ती', 'कॉलेज प्रवेश + छात्रवृत्ति',
   'Apply for an engineering college admission scholarship, reusing verified domicile/identity and triggering income verification if needed.'),
  ('start_small_business', 'Starting a Small Business',
   'लघु व्यवसाय सुरू करणे', 'छोटा व्यवसाय शुरू करना',
   'Register a shop/establishment and obtain the permissions needed to legally operate.'),
  ('farmer_support', 'Farmer Support / Agricultural Benefit', 'शेतकरी सहाय्य', 'किसान सहायता',
   'Access agricultural benefit schemes tied to land records and identity.'),
  ('family_civil_certificates', 'Family / Civil Certificates', 'कौटुंबिक/नागरी दाखले', 'पारिवारिक/नागरिक प्रमाणपत्र',
   'Birth, death, marriage and residence certificates for a household.'),
  ('employment_skill_registration', 'Employment / Skill Registration', 'रोजगार/कौशल्य नोंदणी', 'रोजगार/कौशल्य पंजीकरण',
   'Register for skill development and employment exchange services.')
on conflict (code) do nothing;

-- College Admission + Scholarship dependency graph:
--   identity_verification, domicile_certificate, caste_certificate,
--   income_certificate -> independent documents (each verified/missing
--   on its own; no cross-gating between them)
--   education_scholarship -> the only gated step, blocked until
--   income_certificate is verified
insert into service_dependencies (life_event_id, service_id, depends_on_service_id, sequence_order)
select le.id, s.id, dep.id, seq
from (values
  ('college_admission_scholarship', 'identity_verification', null, 1),
  ('college_admission_scholarship', 'domicile_certificate', null, 2),
  ('college_admission_scholarship', 'caste_certificate', null, 3),
  ('college_admission_scholarship', 'income_certificate', null, 4),
  ('college_admission_scholarship', 'education_scholarship', 'income_certificate', 5)
) as v(event_code, service_code, dep_code, seq)
join life_events le on le.code = v.event_code
join services s on s.code = v.service_code
left join services dep on dep.code = v.dep_code
on conflict do nothing;

-- Starting a Small Business dependency graph
insert into service_dependencies (life_event_id, service_id, depends_on_service_id, sequence_order)
select le.id, s.id, dep.id, seq
from (values
  ('start_small_business', 'business_registration', null, 1),
  ('start_small_business', 'local_noc', 'business_registration', 2),
  ('start_small_business', 'gst_registration', 'business_registration', 3)
) as v(event_code, service_code, dep_code, seq)
join life_events le on le.code = v.event_code
join services s on s.code = v.service_code
left join services dep on dep.code = v.dep_code
on conflict do nothing;
