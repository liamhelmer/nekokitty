# Original owner discovery questions — archived

This is the original discovery questionnaire and is retained as historical
context. Many items marked **blocking** have been answered and must not be treated
as current blockers. The durable answers are in
[`docs/decisions/2026-07-13-owner-decisions.md`](decisions/2026-07-13-owner-decisions.md),
and the canonical unresolved inputs are in
[`docs/plan/2026-07-13-implementation-plan.md`](plan/2026-07-13-implementation-plan.md).
Unknown/TBD remains useful only for questions repeated in that current plan.

## Original immediate deployment blockers — superseded where answered

1. **Blocking — use/license:** Is Neko strictly a personal, noncommercial
   research project, or could it be used commercially, for paid rides/events,
   promotion, a public installation, or a product? Audex's current license is
   noncommercial, and ZipDepth checkpoint provenance also needs clarification
   before commercial/public deployment.
2. **Blocking — model residency:** When you say both models must be “on here” and
   start at boot, is it acceptable for both to be installed and supervised but
   only one profile to be resident at a time? Recommendation: Gemma loads at
   normal boot; Audex is an explicit experimental profile because its complete
   released speech path cannot fit in 8 GB unquantized.
3. **Blocking — Audex fallback:** If Audex must provide its full speech behavior,
   may that profile run on a separate 24–32+ GB NVIDIA computer/cloud GPU while
   the cart retains Gemma/offline commands locally?
4. **Blocking — sudo:** Can you run the documented sudo commands locally, or
   establish a sudo credential in a terminal for the next setup pass? Current
   noninteractive commands cannot switch to headless boot, install system
   dependencies, add Docker access, or enable system services.
5. **Blocking — headless confirmation:** You approved removing X/GNOME/Firefox.
   Should the machine permanently boot to `multi-user.target`, with SSH/console
   as its administration path and graphical mode kept only as a rollback?
6. **Blocking — Git:** May this directory be initialized as a Git repository?
   If yes, should it remain local, or which private remote should eventually hold
   code/config (never models, keys, private audio, or recordings)?
7. **Blocking — storage layout:** Is the root NVMe the intended durable model
   store? Recommendation: `/home/neko/models` on NVMe for pinned runtime
   artifacts; project source here; stories/assets in a separate backed-up data
   directory. What is `/media/neko/disk` intended for?
8. **Blocking — power/cooling:** Is sustained use of the current maximum 15 W
   nvpmodel mode acceptable, and what fan/heatsink/enclosure airflow will exist
   inside the cat body? Is there a maximum skin/enclosure temperature or noise
   level?

## Cart motion and safety scope

9. Does this cart carry people? Is it stationary, manually driven, remotely
   driven, assisted, or autonomous while the assistant operates?
10. What are maximum speed, mass/load, slope, and conservative braking distance?
11. Is proximity strictly for social behavior, or may it affect navigation or
   stopping? Recommendation: social only; an independent qualified controller
   owns all motion safety.
12. What motion controller, safety MCU/PLC, e-stop, watchdog, bumpers, motor
   controller, and obstacle sensors already exist? Which interfaces/protocols are
   available, and may the assistant receive read-only state such as
   stationary/moving/emergency?
13. Where will Neko operate: private indoor space, home, events, sidewalks,
   public road/parking areas, schools, around children, rain/fog, direct sun, and
   day/night? Which jurisdictions matter?
14. Is this a prototype only, or should hardware/software choices anticipate
   formal product safety, accessibility, radio, and privacy compliance?

## Proximity and vision

15. Why is ZipDepth specifically desired: its visual depth effect/research value,
   nearest-person ranking, or an expectation of metre-based proximity? It cannot
   supply metric range by itself.
16. What greeting/sensing range and accuracy are wanted: for example 0.2–2 m,
   0.5–6 m, or farther? Forward-only, side coverage, rear coverage, or 360°?
17. Must it detect/track adults, children, seated/crouched people, groups, pets,
   wheelchairs, and people partly occluded by the cart?
18. Which camera/depth/radar/ToF/lidar/ultrasonic hardware is already purchased
   or planned? The only current development camera detected is a monocular C922.
19. Is an OAK-D/OAK4 stereo spatial camera acceptable? What additional
   perception power budget is available: roughly 3–5 W, 10–15 W, or more?
20. Would mmWave be acceptable for darkness/blind spots, and are there mounting
   constraints in the cat body?
21. May RGB frames be processed at all? May they be stored? Would you prefer a
   smart camera to send only anonymous track IDs and XYZ metadata to the Jetson?
22. Define initial social semantics: greeting enter/exit distance, dwell time,
   approach requirement, cooldown, maximum greetings per hour, quiet hours, and
   whether proactive speech is ever allowed while moving.

## Audio hardware and interaction environment

23. What exact microphone/array, USB/I2S DAC, amplifier, speaker(s), transducer,
   and transducer amplifier will ship? Include models, impedance/power ratings,
   placement, and whether they are already connected.
24. Is a hardware AEC/beamforming DSP acceptable? How far will people speak from
   Neko, from which direction, and how loud are motors, fans, wind, music, and
   road noise at that position?
25. Must it support full duplex/barge-in while Neko speaks/purrs, or may it pause
   output briefly to listen? Recommendation: design for barge-in, with a robust
   hardware echo reference.
26. What wake phrase(s) do you want? Should a button/touch/proximity gesture also
   start listening? Should wake word be disabled during stories or just use a
   stricter threshold?
27. Which languages, accents, dialects, and code-switching are required? Does it
   need speech translation?
28. Desired listening/response targets: boot-to-ready, end-of-turn to first
   audible speech, maximum tolerated pause, and barge-in stop latency?

## Neko's voice and character

29. Describe the spoken voice with references/adjectives: age impression,
   pitch, accent, natural vs robotic, mischievous/calm/childlike, energy, and how
   strongly “cat-like” it should be while staying intelligible.
30. Do you have original/consented voice recordings for a custom voice? Who owns
   them, and may they be processed locally or by a cloud training service?
31. Are there character rules, prohibited topics, preferred vocabulary, name and
   pronoun conventions, catchphrases, or maximum response length? Should it
   literally say “meow” in speech, use samples, or both?
32. Do you have licensed meow/purr/trill recordings? If not, may we create/record
   an original soundbank? What purr intensity/duration should the body transducer
   produce, and are there comfort/noise constraints for passengers/animals?
33. Should Neko identify and remember individual people? Recommendation: no face
   or voice identity by default; opt-in owner profiles only if there is a clear
   need and retention policy.

## Stories and content

34. Who is the story audience and age range? Should there be child-safe and adult
   modes, and how are they selected/locked?
35. What library already exists (recordings, EPUB/text, PDFs), where is it, and
   what licenses/ownership apply? Which jurisdictions determine public-domain
   status?
36. For each source, which modes are allowed: exact recording, exact narration,
   or remix? What modifications are wanted—listener name, setting, length,
   difficulty, moral, character substitution—and what must never change?
37. Should progress/bookmarks sync across sessions? Are multiple user profiles
   needed? Is Audiobookshelf acceptable, or is a small local library sufficient?
38. May generated variants be saved, and for how long? Should owners be able to
   review/delete/export story history?

## Online mode, privacy, and accounts

39. Which cloud model providers/accounts are allowed (OpenAI, Anthropic/Z.AI,
   Google, self-hosted, others), and what monthly cost/rate limits apply?
40. What may leave the device: transcript text, audio clips, still images, video,
   approximate location, sensor metadata, story content? Recommendation: text
   only by default after local wake/ASR, with no bystander media.
41. Is a physical strict-offline switch required? Should it electrically disable
   radios, enforce a firewall/namespace policy, or simply change assistant
   routing? What indicators should show mic, camera, recording, and cloud use?
42. May any audio/image/transcript be stored for debugging? If yes, opt-in method,
   encryption, retention period, access, automatic expiry, and treatment of
   bystanders/minors?
43. Should the microphone have a physical electrical kill and the camera a
   shutter? Recommendation: yes, with visible state independent of software.
44. What connectivity exists on the cart: Wi-Fi, Ethernet, phone hotspot,
   cellular modem? How often is it offline, and is location/current information
   desired online?
45. Should online mode proactively fetch anything, or only use the cloud after a
   user request? Are there topics/tasks that must always stay local?

## Software integration and operations

46. Is ROS 2 already installed/used? Which distribution, nodes, topics/actions,
   and motion/sensor APIs exist? On this Ubuntu 24.04 host, Jazzy is the pragmatic
   baseline if ROS is introduced.
47. Is Home Assistant, MQTT, CAN, serial, GPIO, I2C, or another automation bus
   part of the cart? Which actions may the assistant request?
48. Should model/API endpoints be reachable only on localhost, on a private LAN,
   or remotely? Who needs an administration/dashboard UI?
49. What is the expected operating duty cycle and battery budget: minutes/hours,
   always-on at events, sleep/wake behavior, and acceptable idle power?
50. How should updates happen: manual maintenance, signed automatic OTA, or
   staged updates with rollback? Is remote recovery/SSH/VPN required?
51. Where should health logs and metrics go, for how long, and should raw user
   text be redacted? Who is allowed to read them?
52. What failure experience is desired? Recommendation: if LLM/ASR/depth fails,
   Neko still responds to mute/stop/basic buttons, can make a short local sound,
   and clearly enters degraded mode without a restart loop.

## Historical first answer batch — superseded

This batch was requested during initial discovery. Do not ask it again wholesale;
use the decisions record and the implementation plan's current owner-input list.
