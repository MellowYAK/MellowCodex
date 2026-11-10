---
name: ember-video-services
description: Control Ember Video standard and optional image services from MellowCodex.
---

Use E:\EmberVideo\app.venv Python and ember_video.manage; never kill unknown processes.
Standard: voice_service,video_gateway,video_panel,video_relay.
Extended: text_image_service,image_video_service.
Status: snapshot(). Start: start_selected(names). Stop: control_one(name,stop).
Stop group in order voice_service,text_image_service,image_video_service,video_relay,video_gateway,video_panel filtered to selected group.
Restart is safe stop then start. Respect active-job guards. Relay optional.
Standard start never enables image generators. Image-video is admission toggle.
Verify status after changes. Do not start anything merely to test the skill.
