obs = obslua

source_name   = ""
control_name  = ""
target_hour   = 23
target_minute = 0
stop_text     = ""
last_text     = ""

-- If a control source is set, read "HH:MM" from its text and use that as the
-- target. This is the websocket bridge: a client sets the control source's
-- text via SetInputSettings, and we pick it up on the next tick.
function read_control_target()
	if control_name == "" then
		return
	end
	local source = obs.obs_get_source_by_name(control_name)
	if source == nil then
		return
	end
	local settings = obs.obs_source_get_settings(source)
	local txt = obs.obs_data_get_string(settings, "text")
	obs.obs_data_release(settings)
	obs.obs_source_release(source)

	local h, m = string.match(txt or "", "^%s*(%d%d?):(%d%d?)%s*$")
	if h ~= nil then
		h = tonumber(h)
		m = tonumber(m)
		if h >= 0 and h <= 23 and m >= 0 and m <= 59 then
			target_hour   = h
			target_minute = m
		end
	end
end

-- Seconds remaining until the next occurrence of target_hour:target_minute.
function seconds_until_target()
	local now = os.time()
	local t   = os.date("*t", now)
	t.hour    = target_hour
	t.min     = target_minute
	t.sec     = 0
	local target = os.time(t)
	-- If the target time has already passed today, return 0 (show final text).
	-- Change `return 0` to `target = target + 86400` if you'd rather roll to tomorrow.
	if target <= now then
		return 0
	end
	return target - now
end

function set_time_text()
	local remaining = seconds_until_target()

	local seconds = math.floor(remaining % 60)
	local minutes = math.floor((remaining / 60) % 60)
	local hours   = math.floor(remaining / 3600)
	local text    = string.format("%02d:%02d:%02d", hours, minutes, seconds)

	if remaining < 1 then
		text = stop_text
	end

	if text ~= last_text then
		local source = obs.obs_get_source_by_name(source_name)
		if source ~= nil then
			local settings = obs.obs_data_create()
			obs.obs_data_set_string(settings, "text", text)
			obs.obs_source_update(source, settings)
			obs.obs_data_release(settings)
			obs.obs_source_release(source)
		end
		last_text = text
	end
end

function timer_callback()
	read_control_target()
	set_time_text()
end

----------------------------------------------------------

function script_properties()
	local props = obs.obs_properties_create()

	obs.obs_properties_add_int(props, "target_hour", "Target hour (0-23)", 0, 23, 1)
	obs.obs_properties_add_int(props, "target_minute", "Target minute (0-59)", 0, 59, 1)

	local p = obs.obs_properties_add_list(props, "source", "Text Source",
		obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
	local sources = obs.obs_enum_sources()
	if sources ~= nil then
		for _, source in ipairs(sources) do
			local source_id = obs.obs_source_get_unversioned_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source" then
				local name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(p, name, name)
			end
		end
	end
	obs.source_list_release(sources)

	local c = obs.obs_properties_add_list(props, "control", "Control Source (optional, set via websocket)",
		obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_list_add_string(c, "(none)", "")
	local csources = obs.obs_enum_sources()
	if csources ~= nil then
		for _, source in ipairs(csources) do
			local source_id = obs.obs_source_get_unversioned_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source" then
				local name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(c, name, name)
			end
		end
	end
	obs.source_list_release(csources)

	obs.obs_properties_add_text(props, "stop_text", "Final Text", obs.OBS_TEXT_DEFAULT)

	return props
end

function script_description()
	return "Counts down to a fixed time of day (e.g. 23:00) on a Text source.\n\nClock-based: switching scenes never restarts it."
end

function script_update(settings)
	target_hour   = obs.obs_data_get_int(settings, "target_hour")
	target_minute = obs.obs_data_get_int(settings, "target_minute")
	source_name   = obs.obs_data_get_string(settings, "source")
	control_name  = obs.obs_data_get_string(settings, "control")
	stop_text     = obs.obs_data_get_string(settings, "stop_text")
	last_text     = ""
	read_control_target()
	set_time_text()
end

function script_defaults(settings)
	obs.obs_data_set_default_int(settings, "target_hour", 23)
	obs.obs_data_set_default_int(settings, "target_minute", 0)
	obs.obs_data_set_default_string(settings, "stop_text", "Starting soon (tm)")
end

function script_load(settings)
	-- Update once per second regardless of scene activation, so reactivating
	-- a scene never restarts the countdown — it's always derived from the clock.
	obs.timer_add(timer_callback, 1000)
end
