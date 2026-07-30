import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const outputDir = "/Users/tunwailin/Documents/Capstone/outputs/duplicate-review-2026-07-22";
const outputPath = `${outputDir}/airbus_ad_duplicate_manual_review.xlsx`;
await fs.mkdir(outputDir, { recursive: true });

const d = (iso) => new Date(`${iso}T00:00:00Z`);

const conflictRows = [
  {
    group: 1,
    role: "Correctly parsed predecessor",
    file: "2006-0047__AD_2006-0047_1__easa_ad_2006_0047_superseded.pdf",
    reportedAd: "2006-0047",
    verifiedAd: "2006-0047",
    correction: "No",
    date: d("2006-02-16"),
    subject: "ATA 25 — A330 cockpit instrument-panel bracket; inspection and reinforced-bracket replacement.",
    relationship: "Predecessor; directly superseded by 2007-0281.",
    url: "https://drive.google.com/file/d/1lsYmN76qO3hTX21_FVvYH3PHHxK0pHkb",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 1,
    role: "Misparsed successor",
    file: "2007-0281__AD_2007-0281_1__easa_ad_2007_0281.pdf",
    reportedAd: "2006-0047",
    verifiedAd: "2007-0281",
    correction: "Yes",
    date: d("2007-11-06"),
    subject: "ATA 25 — same bracket; correct fastener torque values for the titanium replacement bracket.",
    relationship: "Direct successor. Header says: This AD supersedes EASA AD 2006-0047.",
    url: "https://drive.google.com/file/d/1y-bfXX1U57QalgC6Q-uV3aGaT1l_lgLg",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2007-0281; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
  {
    group: 2,
    role: "Correctly parsed predecessor",
    file: "2006-0107__AD_2006-0107_1__easa_ad_2006_0107_superseded.pdf",
    reportedAd: "2006-0107",
    verifiedAd: "2006-0107",
    correction: "No",
    date: d("2006-05-12"),
    subject: "ATA 57 — A330/A340 wing shroud-box bottom panel; one-time detailed inspection.",
    relationship: "Predecessor; directly superseded by 2008-0002.",
    url: "https://drive.google.com/file/d/1m4_OCU1bojGgfL_uMg72zwDy1rHivtD-",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 2,
    role: "Misparsed successor",
    file: "2008-0002__AD_2008-0002_1__easa_ad_2008_0002.pdf",
    reportedAd: "2006-0107",
    verifiedAd: "2008-0002",
    correction: "Yes",
    date: d("2008-01-07"),
    subject: "ATA 57 — bolted shroud-box bottom-panel modification replacing the inspection-only action.",
    relationship: "Direct successor. Supersedure field names EASA AD 2006-0107.",
    url: "https://drive.google.com/file/d/1_genvoVVMtPF6E74FqOSTAz_j3o3oQT1",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2008-0002; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
  {
    group: 3,
    role: "Correctly parsed predecessor",
    file: "2006-0108__AD_2006-0108_1__easa_ad_2006_0108_superseded.pdf",
    reportedAd: "2006-0108",
    verifiedAd: "2006-0108",
    correction: "No",
    date: d("2006-05-03"),
    subject: "ATA 31 — EIS2/TCAS display operational limitations.",
    relationship: "Predecessor; directly superseded by 2008-0032.",
    url: "https://drive.google.com/file/d/1M_yQnZ6gLp4fZhSs3O6M0Uht1sQDvauB",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 3,
    role: "Misparsed successor",
    file: "2008-0032__AD_2008-0032_1__easa_ad_2008_0032.pdf",
    reportedAd: "2006-0108",
    verifiedAd: "2008-0032",
    correction: "Yes",
    date: d("2008-02-21"),
    subject: "ATA 31 — installation of improved EIS2 software standard S7.",
    relationship: "Direct successor. Supersedure field names EASA AD 2006-0108.",
    url: "https://drive.google.com/file/d/1M2cKUjR6HXAEaCerw5wztI_feHDmNAeW",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2008-0032; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
  {
    group: 4,
    role: "Correctly parsed predecessor",
    file: "2006-0129__AD_2006-0129_1__easa_ad_2006_0129_superseded.pdf",
    reportedAd: "2006-0129",
    verifiedAd: "2006-0129",
    correction: "No",
    date: d("2006-05-22"),
    subject: "ATA 05 — A330 ALS Part 1 revision 00, safe-life airworthiness limitations.",
    relationship: "Predecessor; one of three ADs directly superseded by 2007-0133.",
    url: "https://drive.google.com/file/d/1CYlUybIRcVeDj3FPQV_evjmNxGhhReno",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 4,
    role: "Misparsed successor",
    file: "2007-0133__AD_2007-0133_1__easa_ad_2007_0133_superseded.pdf",
    reportedAd: "2006-0129",
    verifiedAd: "2007-0133",
    correction: "Yes",
    date: d("2007-05-11"),
    subject: "ATA 05 — combined A330/A340 ALS Part 1 revision 01.",
    relationship: "Direct successor. Supersedes 2006-0129, 2006-0130, and 2006-0324-E.",
    url: "https://drive.google.com/file/d/1h7kZERuy2HD3B502TJy-l94Ie4WfZzEr",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2007-0133; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
  {
    group: 5,
    role: "Correctly parsed related AD",
    file: "2006-0223__AD_2006-0223_1__easa_ad_2006_0223_superseded.pdf",
    reportedAd: "2006-0223",
    verifiedAd: "2006-0223",
    correction: "No",
    date: d("2006-07-21"),
    subject: "ATA 27 — THSA installation/inspection action under Airbus SB A320-27-1164.",
    relationship: "Related predecessor context, but 2007-0178 does not supersede it; both are later superseded by 2008-0150.",
    url: "https://drive.google.com/file/d/106Vdlj1_sU01zVZx2mcB5XkV9MgGwL6B",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 5,
    role: "Misparsed related follow-on",
    file: "2007-0178__AD_2007-0178_1__easa_ad_2007_0178_superseded.pdf",
    reportedAd: "2006-0223",
    verifiedAd: "2007-0178",
    correction: "Yes",
    date: d("2007-06-22"),
    subject: "ATA 27 — one-time inspection of THSA upper/lower attachments after installation issues were found.",
    relationship: "Related follow-on, not a direct successor: its own field says Supersedure: None.",
    url: "https://drive.google.com/file/d/1tHhi4pbavi-KYcHuCM5lgOcP1uegS2xf",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2007-0178; do not create a direct 2007-0178 → 2006-0223 supersedure edge.",
  },
  {
    group: 6,
    role: "Correctly parsed predecessor",
    file: "2006-0307__AD_2006-0307_1__easa_ad_2006_0307.pdf",
    reportedAd: "2006-0307",
    verifiedAd: "2006-0307",
    correction: "No",
    date: d("2006-10-10"),
    subject: "ATA 05 — A330 damage-tolerant ALI issue 14.",
    relationship: "Predecessor; directly superseded by 2008-0023.",
    url: "https://drive.google.com/file/d/1GyoD5bOFgAi937xDje-6zb1rqnvTv33w",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. Clear the conflict flag after the paired row is corrected and groups are rebuilt.",
  },
  {
    group: 6,
    role: "Misparsed successor",
    file: "2008-0023__AD_2008-0023_1__easa_ad_2008_0023_Superseded.pdf",
    reportedAd: "2006-0307",
    verifiedAd: "2008-0023",
    correction: "Yes",
    date: d("2008-02-06"),
    subject: "ATA 05 — A330 damage-tolerant ALI issue 15 with more restrictive limitations.",
    relationship: "Direct successor. Supersedure field names EASA AD 2006-0307.",
    url: "https://drive.google.com/file/d/1oD9jRLVWayaBLzgUwILeVqVgDB0Xo61z",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2008-0023; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
  {
    group: 7,
    role: "Correctly parsed predecessor",
    file: "2006-0308__AD_2006-0308_1__easa_ad_2006_0308_superseded.pdf",
    reportedAd: "2006-0308",
    verifiedAd: "2006-0308",
    correction: "No",
    date: d("2006-10-10"),
    subject: "ATA 05 — A340 damage-tolerant airworthiness limitations.",
    relationship: "Predecessor; directly superseded by 2007-0158.",
    url: "https://drive.google.com/file/d/1gQAJv7_KYO6tzux-5u-MpgREXtVBJUmJ",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "No AD-number change. PDF metadata title says 2006-0307, but the PDF header and filename identify 2006-0308.",
  },
  {
    group: 7,
    role: "Misparsed successor",
    file: "2007-0158__AD_2007-0158_1__easa_ad_2007_0158_Superseded.pdf",
    reportedAd: "2006-0308",
    verifiedAd: "2007-0158",
    correction: "Yes",
    date: d("2007-06-04"),
    subject: "ATA 05 — A340 damage-tolerant ALI issue 10 with new/revised restrictive tasks.",
    relationship: "Direct successor. Supersedure field names EASA AD 2006-0308.",
    url: "https://drive.google.com/file/d/1ceX4gmN4h2c1gq1wOhjalIikeYI3lpSJ",
    verdict: "False conflict",
    keep: "Yes",
    status: "Verified",
    action: "Set AD/base number to 2007-0158; rebuild logical-version, family, inverse-link, and conflict fields.",
  },
];

const nearRows = [
  {
    pair: 1, adA: "2006-0204", dateA: d("2006-07-11"), adB: "2006-0205", dateB: d("2006-07-11"), similarity: 0.93422,
    classification: "Companion / parallel AD",
    evidence: "Both say Supersedure: none and use the same ATA 28 Fuel Tank Safety / FAL framework.",
    difference: "0204 applies to A330 under TCDS A.004; 0205 applies to A340 under TCDS A.015.",
    keep: "Yes", duplicate: "No", directEdge: "No", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1npzgVv-62xulgGmYhWUI7cM3N6lOt8Q5", urlB: "https://drive.google.com/file/d/1nzOomMvMsGd2Fi5VcunhrfOHTiGkKbUl",
    note: "High similarity comes from parallel requirements for different aircraft families.",
  },
  {
    pair: 2, adA: "2006-0332", dateA: d("2006-10-27"), adB: "2006-0333", dateB: d("2006-10-27"), similarity: 0.94002,
    classification: "Companion / parallel AD",
    evidence: "Both say supersedure is not applicable and share the ATA 53 fuselage-skin inspection/repair rationale.",
    difference: "0332 is A330 with SB A330-53-3161/3162; 0333 is A340-200/-300 with SB A340-53-4166/4167.",
    keep: "Yes", duplicate: "No", directEdge: "No", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1_1mC1mI7VXbLjiO-WczkmjqiibTRr3ab", urlB: "https://drive.google.com/file/d/1rRBkNDPZB3F16xNJ_YXkD4ZvI0PaIFkr",
    note: "Parallel instructions for different type certificates.",
  },
  {
    pair: 3, adA: "2013-0023", dateA: d("2013-02-01"), adB: "2014-0103", dateB: d("2014-05-06"), similarity: 0.92584,
    classification: "Direct supersedure / reissue",
    evidence: "2014-0103 explicitly states that it supersedes EASA AD 2013-0023.",
    difference: "Same ATA 34 AOA-probe conic-plate subject; successor adds action after incorrect flat-plate installations were found.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2014-0103 → 2013-0023", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1Kc1xITQ4gBovULVB4-FXYQV8kqdutuC-", urlB: "https://drive.google.com/file/d/16CbDULCeMYxjqjVpC9-Mt-OuUHfYB6Sk",
    note: "Historical predecessor plus active successor.",
  },
  {
    pair: 4, adA: "2015-0089", dateA: d("2015-05-22"), adB: "2015-0134", dateB: d("2015-07-08"), similarity: 0.93872,
    classification: "Direct supersedure / reissue",
    evidence: "2015-0134 explicitly states that it supersedes EASA AD 2015-0089.",
    difference: "Successor retains the ATA 34 AOA-sensor action and reduces compliance times for UTAS P/N 0861ED2 sensors.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2015-0134 → 2015-0089", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1fdU0PKeqwGEn4GTyQFKAf6PEeg2-yuOq", urlB: "https://drive.google.com/file/d/192AQE54k_mzLrTiFihFkYtcx-_L3fA_q",
    note: "Historical predecessor plus active successor.",
  },
  {
    pair: 5, adA: "2016-0035R1", dateA: d("2018-09-21"), adB: "2019-0243", dateB: d("2019-09-30"), similarity: 0.94622,
    classification: "Direct supersedure / reissue",
    evidence: "2019-0243 explicitly states that it supersedes EASA AD 2016-0035R1.",
    difference: "Same ATA 53 A340 structural modifications; successor adds work tied to Actions 1, 2, and 8 for certain aircraft.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2019-0243 → 2016-0035R1", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1s2zAkYMYr4zRuSP8Tvot8IW-KwnzeHhZ", urlB: "https://drive.google.com/file/d/1a8nSjsWnQFEhyA4wgHLZ9tBbWJWgqRpF",
    note: "Historical revision plus later reissue.",
  },
  {
    pair: 6, adA: "2016-0095", dateA: d("2016-05-19"), adB: "2017-0013", dateB: d("2017-01-27"), similarity: 0.97426,
    classification: "Direct supersedure / reissue",
    evidence: "2017-0013 explicitly states that it supersedes EASA AD 2016-0095.",
    difference: "Successor changes the service-life calculation for one RH outboard flap and removes one middle-flap serial number.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2017-0013 → 2016-0095", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1GpkEVvqAbirH3CW5REbgBLOjNxlMByFN", urlB: "https://drive.google.com/file/d/1xaZztZABkKh4c8BSnd-Xq18wPPBhQ652",
    note: "Same ATA 57 A380 flap subject; requirements changed.",
  },
  {
    pair: 7, adA: "2016-0231", dateA: d("2016-11-22"), adB: "2022-0189", dateB: d("2022-09-19"), similarity: 0.97577,
    classification: "Direct supersedure / reissue",
    evidence: "2022-0189 explicitly states that it supersedes EASA AD 2016-0231.",
    difference: "Successor adds A330-743L applicability and tightens the allowance for installing affected flaps.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2022-0189 → 2016-0231", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1Fm6ueZTONXZnbLajnwVZkBkExfDfaKN1", urlB: "https://drive.google.com/file/d/10Hh4xa9H-sQ4uOzBB-j097ARrmzrghlH",
    note: "Same ATA 57 A330/A340 inboard-flap subject; requirements changed.",
  },
  {
    pair: 8, adA: "2017-0138", dateA: d("2017-08-02"), adB: "2017-0251", dateB: d("2017-12-15"), similarity: 0.94550,
    classification: "Direct supersedure / reissue",
    evidence: "2017-0251 explicitly states that it supersedes EASA AD 2017-0138.",
    difference: "Successor adds a Goodrich SB and requirements for engines with the TRF four-lug configuration.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2017-0251 → 2017-0138", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1Vd9tSueW0r9JgIRb1edHg15gZN4pkHQv", urlB: "https://drive.google.com/file/d/1-7Deute4fDbuNS1GOArSDVltapL3BETW",
    note: "Same ATA 71 aft engine-mount retainer subject; requirements changed.",
  },
  {
    pair: 9, adA: "2019-0243", dateA: d("2019-09-30"), adB: "2026-0084", dateB: d("2026-04-27"), similarity: 0.92640,
    classification: "Direct supersedure / reissue",
    evidence: "2026-0084 explicitly states that it supersedes EASA AD 2019-0243.",
    difference: "Successor adds Airbus SB references and a more restrictive Action 5 compliance time for Group 43A aircraft.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2026-0084 → 2019-0243", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1a8nSjsWnQFEhyA4wgHLZ9tBbWJWgqRpF", urlB: "https://drive.google.com/file/d/1lU1lMk3ws0eYX-OU_PAK0WRezUmEs2X1",
    note: "Same ATA 53 A340 structural-modification lineage.",
  },
  {
    pair: 10, adA: "2020-0174", dateA: d("2020-08-05"), adB: "2021-0229", dateB: d("2021-11-05"), similarity: 0.98096,
    classification: "Direct supersedure / reissue",
    evidence: "2021-0229 explicitly states that it supersedes EASA AD 2020-0174.",
    difference: "Same ATA 57 outer-flap/tab subject; successor corrects part serial numbers, updates the SB, and clarifies formatting.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2021-0229 → 2020-0174", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1v9b5jk2YF7_sRV2IX7Lr-yO1bri0Cs6x", urlB: "https://drive.google.com/file/d/1TKEdOUtTP_zz5ghRtjVarn-EfsCzMavM",
    note: "Nearly identical text is expected because the later AD retains the earlier requirements.",
  },
  {
    pair: 11, adA: "2022-0096R2", dateA: d("2024-04-12"), adB: "2024-0091R1", dateB: d("2024-05-30"), similarity: 0.93522,
    classification: "Successor via revised reissue",
    evidence: "2024-0091R1 revises 2024-0091, whose header relationship states that it superseded 2022-0096R2.",
    difference: "Same ATA 22 Flight Guidance subject; the new AD corrects software references, and R1 adds optional SB paths/removes unaffected FG entries.",
    keep: "Yes", duplicate: "No", directEdge: "Family edge: 2024-0091 → 2022-0096R2", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1j6xNE5F49KPXdbUj5zaGIkSZXYMaFyHH", urlB: "https://drive.google.com/file/d/1xP4tUBykQVwPlDpHaRl7_KJgeOK7FxZj",
    note: "Do not describe the exact R1 PDF as an ordinary direct reissue; preserve the 2024-0091 family step.",
  },
  {
    pair: 12, adA: "2023-0212", dateA: d("2023-12-06"), adB: "2024-0217", dateB: d("2024-11-18"), similarity: 0.92824,
    classification: "Direct supersedure / reissue",
    evidence: "2024-0217 explicitly states that it supersedes EASA AD 2023-0212.",
    difference: "Same ATA 53 frame 16/20 double-joggle subject; successor corrects repaired-aircraft treatment and adds inspection-continuation rules.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2024-0217 → 2023-0212", verified: "Yes",
    urlA: "https://drive.google.com/file/d/10VqbdwU6faOfNv3mdGWoMiV16R2hJjTc", urlB: "https://drive.google.com/file/d/1nIpdEqqR12HzkfP4Y0XFu-WSXNPxDifA",
    note: "Historical predecessor plus corrected successor.",
  },
  {
    pair: 13, adA: "2024-0027", dateA: d("2024-01-25"), adB: "2024-0230", dateB: d("2024-12-02"), similarity: 0.92020,
    classification: "Direct supersedure / reissue",
    evidence: "2024-0230 explicitly states that it supersedes EASA AD 2024-0027.",
    difference: "Same ATA 57 wing-skin inspection; successor prohibits deactivated SRM tasks and permits the May-2024-or-later task version.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2024-0230 → 2024-0027", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1mUvaT4h45kKRXwWytsM4XB5SVMXhhBiK", urlB: "https://drive.google.com/file/d/1ZN9xR77wWuQk6cpaxKfCkvvfpTKdCatk",
    note: "Historical predecessor plus updated successor.",
  },
  {
    pair: 14, adA: "2024-0038", dateA: d("2024-02-05"), adB: "2025-0068", dateB: d("2025-03-28"), similarity: 0.96602,
    classification: "Direct supersedure / reissue",
    evidence: "2025-0068 explicitly states that it supersedes EASA AD 2024-0038.",
    difference: "Same ATA 25 galley inspection; successor adds three omitted part numbers and removes P/N 6019A3-000101.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2025-0068 → 2024-0038", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1h3yAuyRGLgBW7Pf7DqirucYqmRyfuCU1", urlB: "https://drive.google.com/file/d/1DqNuvBWiyJmstYGzv4meQIdl0eaUp1Qn",
    note: "First direct edge in the three-document galley lineage.",
  },
  {
    pair: 15, adA: "2024-0038", dateA: d("2024-02-05"), adB: "2026-0017", dateB: d("2026-01-23"), similarity: 0.95868,
    classification: "Transitive lineage (two-hop)",
    evidence: "2026-0017 supersedes 2025-0068, which supersedes 2024-0038; it does not directly supersede 2024-0038.",
    difference: "Same galley subject; the latest AD adds another affected part number after the intermediate 2025 reissue.",
    keep: "Yes", duplicate: "No", directEdge: "No: preserve 2024-0038 → 2025-0068 → 2026-0017", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1h3yAuyRGLgBW7Pf7DqirucYqmRyfuCU1", urlB: "https://drive.google.com/file/d/1Dvr81oPyBz-A-UBCgJwVWEfYqnSoNOIh",
    note: "Similarity produced a valid lineage pair, but it must not become a direct supersedure edge.",
  },
  {
    pair: 16, adA: "2024-0199", dateA: d("2024-10-18"), adB: "2025-0120", dateB: d("2025-05-26"), similarity: 0.94714,
    classification: "Direct supersedure / reissue",
    evidence: "2025-0120 explicitly states that it supersedes EASA AD 2024-0199.",
    difference: "Same ATA 44 antenna-adapter-plate inspection; successor extends applicability by adding A321-271NY.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2025-0120 → 2024-0199", verified: "Yes",
    urlA: "https://drive.google.com/file/d/10cb3_WU91C01LytOrme9kxRtARJuwlje", urlB: "https://drive.google.com/file/d/1TCFYTHnyLNooMItYFDdXqK3G16x1nXjA",
    note: "Historical predecessor plus expanded-applicability successor.",
  },
  {
    pair: 17, adA: "2025-0068", dateA: d("2025-03-28"), adB: "2026-0017", dateB: d("2026-01-23"), similarity: 0.98877,
    classification: "Direct supersedure / reissue",
    evidence: "2026-0017 explicitly states that it supersedes EASA AD 2025-0068.",
    difference: "Same ATA 25 galley inspection; successor adds galley P/N 6019F2-000001.",
    keep: "Yes", duplicate: "No", directEdge: "Yes: 2026-0017 → 2025-0068", verified: "Yes",
    urlA: "https://drive.google.com/file/d/1DqNuvBWiyJmstYGzv4meQIdl0eaUp1Qn", urlB: "https://drive.google.com/file/d/1Dvr81oPyBz-A-UBCgJwVWEfYqnSoNOIh",
    note: "Second direct edge in the three-document galley lineage.",
  },
];

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const conflicts = workbook.worksheets.add("Same-Version Review");
const near = workbook.worksheets.add("Near-Duplicate Review");
const parser = workbook.worksheets.add("Parser Fix");

const colors = {
  navy: "#0F2942",
  blue: "#2563EB",
  teal: "#0F766E",
  green: "#15803D",
  lightGreen: "#DCFCE7",
  amber: "#B45309",
  lightAmber: "#FEF3C7",
  red: "#B42318",
  lightRed: "#FEE2E2",
  slate: "#475569",
  lightSlate: "#E2E8F0",
  paleBlue: "#DBEAFE",
  white: "#FFFFFF",
  text: "#172033",
};

function titleBand(sheet, lastCol, title, subtitle) {
  sheet.mergeCells(`A1:${lastCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 18 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight = 32;
  sheet.mergeCells(`A2:${lastCol}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${lastCol}2`).format = {
    fill: "#EAF2F8",
    font: { color: colors.slate, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${lastCol}2`).format.rowHeight = 30;
  sheet.showGridLines = false;
}

function styleHeader(range) {
  range.format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: "#9FB3C8" },
  };
  range.format.rowHeight = 34;
}

titleBand(
  summary,
  "H",
  "Airbus EASA AD duplicate review — document-level verdicts",
  "Manual review of 14 same-version conflict rows and 17 near-duplicate pairs. Source PDFs were checked for their own header number, Date/Issued field, subject/applicability, and explicit Supersedure/Revision wording. Google Drive source data was not modified.",
);

summary.getRange("A4:B4").merge();
summary.getRange("A4").values = [["Corpus review outcome"]];
summary.getRange("D4:E4").merge();
summary.getRange("D4").values = [["Near-pair classification"]];
summary.getRange("G4:H4").merge();
summary.getRange("G4").values = [["Bottom line"]];
for (const r of ["A4:B4", "D4:E4", "G4:H4"]) {
  summary.getRange(r).format = { fill: colors.teal, font: { bold: true, color: colors.white }, verticalAlignment: "center" };
}

summary.getRange("A5:A10").values = [
  ["Conflict document rows"],
  ["Actual conflict groups"],
  ["AD-number corrections"],
  ["Near pairs reviewed"],
  ["True duplicate pairs"],
  ["Recommended deletions"],
];
summary.getRange("B5").formulas = [["=COUNTA('Same-Version Review'!$A$6:$A$19)"]];
summary.getRange("B6").formulas = [["=B5/2"]];
summary.getRange("B7").formulas = [["=COUNTIF('Same-Version Review'!$F$6:$F$19,\"Yes\")"]];
summary.getRange("B8").formulas = [["=COUNTA('Near-Duplicate Review'!$A$6:$A$22)"]];
summary.getRange("B9").formulas = [["=COUNTIF('Near-Duplicate Review'!$K$6:$K$22,\"Yes\")"]];
summary.getRange("B10").formulas = [["=B9"]];

summary.getRange("D5:D9").values = [
  ["Explicit direct supersedure"],
  ["Successor via revised reissue"],
  ["Transitive lineage"],
  ["Companion / parallel"],
  ["Keep-both decisions"],
];
summary.getRange("E5").formulas = [["=COUNTIF('Near-Duplicate Review'!$G$6:$G$22,\"Direct supersedure / reissue\")"]];
summary.getRange("E6").formulas = [["=COUNTIF('Near-Duplicate Review'!$G$6:$G$22,\"Successor via revised reissue\")"]];
summary.getRange("E7").formulas = [["=COUNTIF('Near-Duplicate Review'!$G$6:$G$22,\"Transitive lineage (two-hop)\")"]];
summary.getRange("E8").formulas = [["=COUNTIF('Near-Duplicate Review'!$G$6:$G$22,\"Companion / parallel AD\")"]];
summary.getRange("E9").formulas = [["=COUNTIF('Near-Duplicate Review'!$J$6:$J$22,\"Yes\")"]];

summary.mergeCells("G5:H10");
summary.getRange("G5").values = [["No reviewed file is a duplicate to delete.\n\nThe 14 conflict rows are seven false groups created by seven wrong AD-number parses.\n\nAll 17 similarity pairs are valid historical/parallel relationships; keep both PDFs in every pair."]];
summary.getRange("G5:H10").format = {
  fill: colors.lightGreen,
  font: { bold: true, color: "#14532D", size: 11 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "medium", color: "#86A886" },
};

summary.getRange("A5:B10").format.borders = { preset: "inside", style: "thin", color: "#D7E0E8" };
summary.getRange("D5:E9").format.borders = { preset: "inside", style: "thin", color: "#D7E0E8" };
summary.getRange("A5:A10").format.font = { color: colors.slate };
summary.getRange("D5:D9").format.font = { color: colors.slate };
summary.getRange("B5:B10").format = { fill: "#F8FAFC", font: { bold: true, color: colors.navy, size: 14 }, horizontalAlignment: "center" };
summary.getRange("E5:E9").format = { fill: "#F8FAFC", font: { bold: true, color: colors.navy, size: 14 }, horizontalAlignment: "center" };

summary.getRange("A12:H12").values = [["Decision area", "Final result", "Reason", null, null, null, null, null]];
summary.mergeCells("C12:H12");
styleHeader(summary.getRange("A12:H12"));
const decisions = [
  ["Same-version conflicts", "False conflicts", "Seven legacy successor/follow-on PDFs were assigned an older referenced AD number; the paired PDFs are distinct and all must remain."],
  ["Near-duplicate pairs", "Keep all 17 pairs", "Thirteen are explicit direct supersedures, one is a revised-successor lineage, one is transitive, and two are companion ADs."],
  ["Supersedure graph", "Use only supported edges", "Do not turn companion or transitive similarity pairs into direct links. Preserve the two direct galley edges and exclude the two-hop shortcut."],
  ["Drive/corpus state", "Read-only", "This workbook records the review. It does not rewrite the manifest, reports, or source PDFs."],
];
summary.getRange("A13:C16").values = decisions;
summary.mergeCells("C13:H13");
summary.mergeCells("C14:H14");
summary.mergeCells("C15:H15");
summary.mergeCells("C16:H16");
summary.getRange("A13:H16").format = { wrapText: true, verticalAlignment: "top" };
summary.getRange("A13:H16").format.rowHeight = 42;
summary.getRange("A13:A16").format.font = { bold: true, color: colors.navy };
summary.getRange("B13:B16").format.font = { bold: true, color: colors.teal };
summary.getRange("A13:H16").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" }, bottom: { style: "thin", color: "#D7E0E8" } };

summary.getRange("A18:H18").merge();
summary.getRange("A18").values = [["Sources and review method"]];
summary.getRange("A18:H18").format = { fill: colors.lightSlate, font: { bold: true, color: colors.navy } };
summary.getRange("A19:B22").values = [
  ["duplicate_review.csv", "https://drive.google.com/file/d/1z1r-hEAkjCFubLF50aMTVOZvCBvk_3XA/view"],
  ["near_duplicate_candidates.csv", "https://drive.google.com/file/d/1aj_dJW6iXB7DOy6x1F67scXT5VoEyBa-/view"],
  ["corpus_manifest.csv", "https://drive.google.com/file/d/1ggUgqy7oxWmbU2yjvmp55qKSvLI_XI2Q/view"],
  ["supersedure_links.csv", "https://drive.google.com/file/d/1u_zoGCCvVbPvTNHq3d9SCQuxTfF71ccF/view"],
];
summary.mergeCells("B19:H19");
summary.mergeCells("B20:H20");
summary.mergeCells("B21:H21");
summary.mergeCells("B22:H22");
summary.getRange("A19:A22").format.font = { bold: true, color: colors.slate };
summary.getRange("B19:H22").format.font = { color: colors.blue };
summary.getRange("A19:H22").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };
summary.getRange("A1:H22").format.verticalAlignment = "center";
summary.getRange("A:A").format.columnWidth = 25;
summary.getRange("B:B").format.columnWidth = 16;
summary.getRange("C:C").format.columnWidth = 20;
summary.getRange("D:D").format.columnWidth = 28;
summary.getRange("E:E").format.columnWidth = 14;
summary.getRange("F:F").format.columnWidth = 4;
summary.getRange("G:H").format.columnWidth = 24;
summary.freezePanes.freezeRows(2);

titleBand(
  conflicts,
  "N",
  "Same-version conflict review — 14 rows / 7 false groups",
  "Every row was checked against the source PDF. The seven newer/follow-on files have a correct own header but were assigned an older body-reference number by the parser.",
);
conflicts.getRange("A4:N4").merge();
conflicts.getRange("A4").values = [["Action rule: retain every PDF; correct only the seven rows marked Yes in AD correction required; then rebuild family/version/conflict fields from cached text."]];
conflicts.getRange("A4:N4").format = { fill: colors.lightAmber, font: { bold: true, color: colors.amber }, wrapText: true };

const conflictHeaders = [[
  "Group", "Row role", "File name", "Reported AD", "Verified AD", "AD correction required", "Header Date / Issued", "Verified subject", "Relationship to paired file", "Source PDF", "Conflict verdict", "Keep PDF", "Manual status", "Manifest action",
]];
conflicts.getRange("A5:N5").values = conflictHeaders;
styleHeader(conflicts.getRange("A5:N5"));
const conflictMatrix = conflictRows.map((r) => [
  r.group, r.role, r.file, r.reportedAd, r.verifiedAd, r.correction, r.date, r.subject, r.relationship, r.url, r.verdict, r.keep, r.status, r.action,
]);
conflicts.getRange(`A6:N${5 + conflictMatrix.length}`).values = conflictMatrix;
conflicts.getRange("G6:G19").format.numberFormat = "yyyy-mm-dd";
conflicts.getRange("A6:N19").format = { wrapText: true, verticalAlignment: "top", font: { size: 9, color: colors.text } };
conflicts.getRange("A6:N19").format.rowHeight = 64;
conflicts.getRange("A6:A19").format.horizontalAlignment = "center";
conflicts.getRange("D6:G19").format.horizontalAlignment = "center";
conflicts.getRange("K6:M19").format.horizontalAlignment = "center";
conflicts.getRange("J6:J19").format.font = { color: colors.blue, size: 8 };
conflicts.getRange("A6:N19").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };
conflicts.getRange("F6:F19").conditionalFormats.add("containsText", { text: "Yes", format: { fill: colors.lightRed, font: { bold: true, color: colors.red } } });
conflicts.getRange("F6:F19").conditionalFormats.add("containsText", { text: "No", format: { fill: colors.lightGreen, font: { color: colors.green } } });
conflicts.getRange("K6:K19").conditionalFormats.add("containsText", { text: "False", format: { fill: colors.lightGreen, font: { bold: true, color: colors.green } } });
conflicts.getRange("A:A").format.columnWidth = 8;
conflicts.getRange("B:B").format.columnWidth = 24;
conflicts.getRange("C:C").format.columnWidth = 52;
conflicts.getRange("D:E").format.columnWidth = 14;
conflicts.getRange("F:F").format.columnWidth = 14;
conflicts.getRange("G:G").format.columnWidth = 14;
conflicts.getRange("H:H").format.columnWidth = 46;
conflicts.getRange("I:I").format.columnWidth = 50;
conflicts.getRange("J:J").format.columnWidth = 30;
conflicts.getRange("K:K").format.columnWidth = 16;
conflicts.getRange("L:L").format.columnWidth = 10;
conflicts.getRange("M:M").format.columnWidth = 14;
conflicts.getRange("N:N").format.columnWidth = 52;
conflicts.tables.add("A5:N19", true, "SameVersionReviewTable");
conflicts.freezePanes.freezeRows(5);
conflicts.freezePanes.freezeColumns(2);

titleBand(
  near,
  "P",
  "Near-duplicate review — 17 pairs checked one by one",
  "All source PDF headers match their filenames. Similarity is explained by direct supersedure, inherited/transitive lineage, or parallel requirements for different aircraft families. No pair is a deletion duplicate.",
);
near.getRange("A4:P4").merge();
near.getRange("A4").values = [["Graph rule: explicit direct edges may be recorded; companion pairs and the 2024-0038 → 2026-0017 transitive shortcut must not be recorded as direct supersedures."]];
near.getRange("A4:P4").format = { fill: colors.paleBlue, font: { bold: true, color: colors.navy }, wrapText: true };

const nearHeaders = [[
  "Pair", "AD A", "Date / Issued A", "AD B", "Date / Issued B", "Text similarity", "Final classification", "Relationship evidence", "Material difference", "Keep both", "True duplicate", "Direct graph edge", "Manually verified", "PDF A", "PDF B", "Reviewer note",
]];
near.getRange("A5:P5").values = nearHeaders;
styleHeader(near.getRange("A5:P5"));
const nearMatrix = nearRows.map((r) => [
  r.pair, r.adA, r.dateA, r.adB, r.dateB, r.similarity, r.classification, r.evidence, r.difference, r.keep, r.duplicate, r.directEdge, r.verified, r.urlA, r.urlB, r.note,
]);
near.getRange(`A6:P${5 + nearMatrix.length}`).values = nearMatrix;
near.getRange("C6:C22").format.numberFormat = "yyyy-mm-dd";
near.getRange("E6:E22").format.numberFormat = "yyyy-mm-dd";
near.getRange("F6:F22").format.numberFormat = "0.00000";
near.getRange("A6:P22").format = { wrapText: true, verticalAlignment: "top", font: { size: 9, color: colors.text } };
near.getRange("A6:P22").format.rowHeight = 76;
near.getRange("A6:A22").format.horizontalAlignment = "center";
near.getRange("B6:F22").format.horizontalAlignment = "center";
near.getRange("J6:M22").format.horizontalAlignment = "center";
near.getRange("N6:O22").format.font = { color: colors.blue, size: 8 };
near.getRange("A6:P22").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };
near.getRange("G6:G22").conditionalFormats.add("containsText", { text: "Direct", format: { fill: colors.paleBlue, font: { bold: true, color: "#1D4ED8" } } });
near.getRange("G6:G22").conditionalFormats.add("containsText", { text: "Companion", format: { fill: colors.lightAmber, font: { bold: true, color: colors.amber } } });
near.getRange("G6:G22").conditionalFormats.add("containsText", { text: "Transitive", format: { fill: colors.lightSlate, font: { bold: true, color: colors.slate } } });
near.getRange("G6:G22").conditionalFormats.add("containsText", { text: "Successor", format: { fill: "#EDE9FE", font: { bold: true, color: "#6D28D9" } } });
near.getRange("K6:K22").conditionalFormats.add("containsText", { text: "No", format: { fill: colors.lightGreen, font: { bold: true, color: colors.green } } });
near.getRange("A:A").format.columnWidth = 7;
near.getRange("B:B").format.columnWidth = 14;
near.getRange("C:C").format.columnWidth = 14;
near.getRange("D:D").format.columnWidth = 14;
near.getRange("E:E").format.columnWidth = 14;
near.getRange("F:F").format.columnWidth = 12;
near.getRange("G:G").format.columnWidth = 31;
near.getRange("H:H").format.columnWidth = 50;
near.getRange("I:I").format.columnWidth = 58;
near.getRange("J:K").format.columnWidth = 12;
near.getRange("L:L").format.columnWidth = 38;
near.getRange("M:M").format.columnWidth = 16;
near.getRange("N:O").format.columnWidth = 30;
near.getRange("P:P").format.columnWidth = 45;
near.tables.add("A5:P22", true, "NearDuplicateReviewTable");
near.freezePanes.freezeRows(5);
near.freezePanes.freezeColumns(2);

titleBand(
  parser,
  "F",
  "Parser correction exposed by the seven false conflict groups",
  "The source PDFs are correct. The current AD_HEADER_RE fails on legacy headers with spaces around the dash, then accepts an older compact body reference as if it were the document's own AD number.",
);
parser.getRange("A4:D4").values = [["Issue", "Document evidence", "Effect", "Recommended correction"]];
styleHeader(parser.getRange("A4:D4"));
const parserFindings = [
  ["Header separator is too strict", "Own headers use forms such as 2007 - 0281 or 2008 – 0032.", "The current year-separator-number pattern does not allow surrounding spaces, so the correct header is skipped.", "Allow \\s* around [-–—_]."],
  ["Header token is too permissive", "Later text contains compact references such as EASA AD 2006-0047.", "Because No. is optional, a body reference satisfies AD_HEADER_RE and is returned with 1.00 confidence.", "Require AD No. for the high-confidence header regex and anchor it to a line on page 1."],
  ["No header/filename mismatch guard", "All seven affected filenames encode the correct AD number, but the older body match overrides them.", "Seven unrelated files are grouped under old logical-version keys, producing 14 conflict rows.", "Parse header and filename independently; if they disagree, flag the row and prefer the anchored own-header/filename consensus."],
  ["Generic fallback can be historical", "AD bodies legitimately cite many earlier ADs.", "A generic first-page number is not safe as a current-document identifier.", "Use generic matching only after both header and filename fail, and keep low confidence/manual review."],
];
parser.getRange("A5:D8").values = parserFindings;
parser.getRange("A5:D8").format = { wrapText: true, verticalAlignment: "top" };
parser.getRange("A5:D8").format.rowHeight = 62;
parser.getRange("A5:D8").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };
parser.getRange("A5:A8").format.font = { bold: true, color: colors.navy };

parser.getRange("A10:F10").merge();
parser.getRange("A10").values = [["Recommended high-confidence header regex"]];
parser.getRange("A10:F10").format = { fill: colors.teal, font: { bold: true, color: colors.white } };
parser.getRange("A11:F18").merge();
parser.getRange("A11").values = [[String.raw`AD_HEADER_RE = re.compile(
    r"""
    (?mix)^\s*
    (?:EASA\s+)?(?:EMERGENCY\s+)?AD\s+No\.?\s*[:#]?\s*
    (?P<year>(?:19|20)\d{2})\s*[-–—_]\s*(?P<number>\d{4})
    (?:\s*[-_]?\s*(?P<revision>R\d+))?
    (?:\s*[-_]?\s*(?P<emergency>E))?\b
    """
)`]];
parser.getRange("A11:F18").format = {
  fill: "#0B1220",
  font: { color: "#D1FAE5", size: 10 },
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "outside", style: "thin", color: "#334155" },
};

parser.getRange("A20:D20").values = [["Rerun step", "Setting / check", "Expected result", "Why"]];
styleHeader(parser.getRange("A20:D20"));
parser.getRange("A21:D25").values = [
  ["1", "Keep FORCE_RESCAN_PDFS = False", "Reuse extracted-text Parquet cache", "The PDFs and extracted text did not change; only parsing/grouping logic changes."],
  ["2", "Recompute AD enrichment and manifest fields", "Seven corrected AD/base numbers", "Cached records must be re-enriched with the new regex before duplicate grouping."],
  ["3", "Rebuild logical-version and family fields", "Seven false groups disappear", "Each corrected row moves to its own true AD family."],
  ["4", "Rebuild supersedure/inverse links", "No false 2007-0178 → 2006-0223 direct edge", "The source says Supersedure: None; a historical body reference is not a direct relationship."],
  ["5", "Re-export review reports", "same_version_content_conflicts should fall from 14 to 0 for these cases", "All fourteen PDFs remain; only seven manifest identities change."],
];
parser.getRange("A21:D25").format = { wrapText: true, verticalAlignment: "top" };
parser.getRange("A21:D25").format.rowHeight = 48;
parser.getRange("A21:D25").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };

parser.getRange("A27:C27").values = [["File currently misparsed", "Current reported AD", "Verified AD"]];
styleHeader(parser.getRange("A27:C27"));
parser.getRange("A28:C34").values = conflictRows.filter((r) => r.correction === "Yes").map((r) => [r.file, r.reportedAd, r.verifiedAd]);
parser.getRange("A28:C34").format = { wrapText: true, verticalAlignment: "top" };
parser.getRange("A28:C34").format.rowHeight = 34;
parser.getRange("B28:C34").format.horizontalAlignment = "center";
parser.getRange("A28:C34").format.borders = { insideHorizontal: { style: "thin", color: "#D7E0E8" } };

parser.getRange("A:A").format.columnWidth = 34;
parser.getRange("B:B").format.columnWidth = 40;
parser.getRange("C:C").format.columnWidth = 44;
parser.getRange("D:D").format.columnWidth = 44;
parser.getRange("E:F").format.columnWidth = 18;
parser.freezePanes.freezeRows(4);

const checks = [];
for (const [sheetName, range] of [
  ["Summary", "A1:H22"],
  ["Same-Version Review", "A1:N19"],
  ["Near-Duplicate Review", "A1:P22"],
  ["Parser Fix", "A1:F34"],
]) {
  const inspection = await workbook.inspect({ kind: "region", sheetId: sheetName, range, maxChars: 3500, tableMaxRows: 8, tableMaxCols: 16, tableMaxCellChars: 100 });
  checks.push({ sheetName, inspection });
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 0.9, format: "png" });
  await fs.writeFile(`${outputDir}/${sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const formulaCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  maxChars: 3000,
});

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

console.log(JSON.stringify({ outputPath, conflictRows: conflictRows.length, nearPairs: nearRows.length, previews: checks.map((c) => c.sheetName), formulaCheck: formulaCheck?.ndjson ?? formulaCheck }, null, 2));
