# coding=utf-8
from __future__ import absolute_import

import logging
import json
import datetime
import os, errno
from os import listdir, unlink
from os.path import isfile, join, isdir

import flask
from octoprint.server.util.flask import redirect_to_tornado
import octoprint.plugin
import octoprint.settings
import time

from .operate import Operate


class TogglePlugin(
        octoprint.plugin.TemplatePlugin, octoprint.plugin.SettingsPlugin,
        octoprint.plugin.StartupPlugin, octoprint.plugin.AssetPlugin,
        octoprint.plugin.BlueprintPlugin, octoprint.plugin.SimpleApiPlugin,
        octoprint.plugin.OctoPrintPlugin):
    def __init__(self):
        self._logger = logging.getLogger("octoprint.plugins.toggle")

    #~~ StartupPlugin
    def on_after_startup(self):
        self.path = self._settings.get(["path"])

    #~~ SettingsPlugin
    def on_settings_save(self, data):
        super(TogglePlugin, self).on_settings_save(data)

    def get_settings_defaults(self):
        return dict(
            path="/etc/toggle/", default_profile=None, debug_logging=False)

    #~~ AssetPlugin API
    def get_assets(self):
        return {
            "js": ["js/toggle.js"],
            "less": ["less/toggle.less"],
            "css": ["css/toggle.css"]
        }

    #~~ SimpleApiPlugin API
    def get_api_commands(self):
        return dict(
            get_profiles=[],
            use_profile=[],
            delete_profile=[],
            restart_toggle=[],
            get_local=[],
            save_local=[])

    def on_api_command(self, command, data):
        o = Operate()
        if command == "get_profiles":
            printers = o.get_printers()
            default = o.get_default_printer()
            profiles = {}
            for printer in printers:
                key, _ = os.path.splitext(printer)
                profiles[printer] = {
                    "displayName": key,
                    "description": key,
                    "default": printer == default,
                    "refs": {
                        "resource":
                        flask.url_for(
                            "plugin.toggle.download_profile",
                            filename=printer,
                            _external=True),
                        "download":
                        flask.url_for("index", _external=True) +
                        "plugin/toggle/download/" + printer
                    }
                }
            return flask.jsonify(**profiles)
        elif command == "use_profile":
            filename = data["key"]
            if (o.choose_printer(filename)):
                return flask.jsonify(ok=1)
            return flask.jsonify(ok=0)
        elif command == "delete_profile":
            filename = data["key"]
            if (o.delete_printer(filename)):
                return flask.jsonify(ok=1)
            return flask.jsonify(ok=0)
        elif command == "restart_toggle":
            o.restart_toggle()
            return flask.jsonify(ok=1)
        elif command == "get_local":
            filename = os.path.join(self._settings.get(["path"]), "local.cfg")
            data = o.get_local(filename)
            return flask.jsonify(data=data)
        elif command == "save_local":
            filename = os.path.join(self._settings.get(["path"]), "local.cfg")
            o.save_local(data["data"], filename)
            return flask.jsonify(ok=1)
        else:
            self._logger.info("Unknown command: '" + str(line) + "'")

    def on_api_get(self, request):
        return flask.jsonify(foo="bar")

    @octoprint.plugin.BlueprintPlugin.route(
        "/profiles/<filename>", methods=["GET"])
    def download_profile(filename):
        return redirect_to_tornado(
            request,
            url_for("index") + "downloads/profiles/" + filename)

    ##~~ BlueprintPlugin API
    @octoprint.plugin.BlueprintPlugin.route("/import", methods=["POST"])
    def import_toggle_profile(self):
        import datetime
        import tempfile

        input_name = "file"
        input_upload_name = input_name + "." + self._settings.global_get(
            ["server", "uploads", "nameSuffix"])
        input_upload_path = input_name + "." + self._settings.global_get(
            ["server", "uploads", "pathSuffix"])

        if input_upload_name in flask.request.values and input_upload_path in flask.request.values:
            filename = flask.request.values[input_upload_name]
            # Parse the Config
            try:
                profile_dict = _check_config_file(
                    flask.request.values[input_upload_path])
            except Exception as e:
                self._logger.exception(
                    "Error while converting the imported profile")
                return flask.make_response(
                    "Something went wrong while converting imported profile: {message}"
                    .format(message=str(e)), 500)

        else:
            self._logger.warn(
                "No profile file included for importing, aborting")
            return flask.make_response("No file included", 400)

        if profile_dict is None:
            self._logger.warn("Could not convert profile, aborting")
            return flask.make_response("Could not convert Toggle profile", 400)

        name, _ = os.path.splitext(filename)

        # default values for name, display name and description
        profile_name = _sanitize_name(name)
        profile_display_name = name
        profile_description = "Imported from {filename} on {date}".format(
            filename=filename,
            date=octoprint.util.get_formatted_datetime(
                datetime.datetime.now()))
        profile_allow_overwrite = False

        # overrides
        if "name" in flask.request.values:
            profile_name = flask.request.values["name"]
        if "displayName" in flask.request.values:
            profile_display_name = flask.request.values["displayName"]
        if "description" in flask.request.values:
            profile_description = flask.request.values["description"]
        if "allowOverwrite" in flask.request.values:
            from octoprint.server.api import valid_boolean_trues
            profile_allow_overwrite = flask.request.values[
                "allowOverwrite"] in valid_boolean_trues

        try:
            from_file = flask.request.values[input_upload_path]
            to_file = "/etc/toggle/" + profile_name + ".cfg"
            self._logger.info("Renaming {} to {}".format(from_file, to_file))
            os.rename(from_file, to_file)
        except IOError as e:
            self._logger.warn("Error renaming file" + str(e))
            return flask.make_response(
                "Error renaming file. Perhaps wrong permissions".format(
                    **locals()), 409)

        result = dict(
            resource=flask.url_for(
                "api.slicingGetSlicerProfile",
                slicer="cura",
                name=profile_name,
                _external=True),
            displayName=profile_display_name,
            description=profile_description)
        r = flask.make_response(flask.jsonify(result), 201)
        r.headers["Location"] = result["resource"]
        return r

    def route_hook(self, server_routes, *args, **kwargs):
        from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
        from octoprint.util import is_hidden_path

        return [(r"/download/(.*)", LargeResponseHandler,
                 dict(
                     path=self._settings.get(["path"]),
                     as_attachment=True,
                     path_validation=path_validation_factory(
                         lambda path: not is_hidden_path(path),
                         status_code=401)))]


def _check_config_file(config_file):
    import ConfigParser
    import logging

    default = ConfigParser.SafeConfigParser()
    default.readfp(open("/etc/toggle/default.cfg"))

    new = ConfigParser.SafeConfigParser()
    new.readfp(open(config_file))

    # Get list of changed values
    for section in new.sections():
        if not default.has_section(section):
            logging.warning("Unknown section in file: {}".format(section))
        for option in new.options(section):
            if not default.has_option(section, option):
                logging.warning("Unknown option in file: {} in {}".format(
                    option, section))

    return True


def _sanitize_name(name):
    if name is None:
        return None

    if "/" in name or "\\" in name:
        raise ValueError("name must not contain / or \\")

    import string
    valid_chars = "-_.() {ascii}{digits}".format(
        ascii=string.ascii_letters, digits=string.digits)
    sanitized_name = ''.join(c for c in name if c in valid_chars)
    sanitized_name = sanitized_name.replace(" ", "_")
    return sanitized_name.lower()


__plugin_name__ = "Toggle Plugin"


def __plugin_load__():
    plugin = TogglePlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {"octoprint.server.http.routes": plugin.route_hook}
