$(function() {
    function ToggleViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.popup = undefined;

        self.fileName = ko.observable();

        self.placeholderName = ko.observable();
        self.placeholderDisplayName = ko.observable();
        self.placeholderDescription = ko.observable();

        self.profileName = ko.observable();
        self.profileDisplayName = ko.observable();
        self.profileDescription = ko.observable();
        self.profileAllowOverwrite = ko.observable(true);

        self.uploadElement = $("#settings-toggle-import");
        self.uploadButton = $("#settings-toggle-import-start");

        self.saveButton = $("#settings-toggle-editor-save");

        self.profiles = new ItemListHelper(
            "plugin_toggle_profiles",
            {
                "id": function(a, b) {
                    if (a["key"].toLocaleLowerCase() < b["key"].toLocaleLowerCase()) return -1;
                    if (a["key"].toLocaleLowerCase() > b["key"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "name": function(a, b) {
                    // sorts ascending
                    var aName = a.name();
                    if (aName === undefined) {
                        aName = "";
                    }
                    var bName = b.name();
                    if (bName === undefined) {
                        bName = "";
                    }

                    if (aName.toLocaleLowerCase() < bName.toLocaleLowerCase()) return -1;
                    if (aName.toLocaleLowerCase() > bName.toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "id",
            [],
            [],
            5
        );

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.uploadElement.fileupload({
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            add: function(e, data) {
                if (data.files.length == 0) {
                    return false;
                }

                self.fileName(data.files[0].name);

                var name = self.fileName().substr(0, self.fileName().lastIndexOf("."));
                self.placeholderName(self._sanitize(name).toLowerCase());
                self.placeholderDisplayName(name);
                self.placeholderDescription("Imported from " + self.fileName() + " on " + formatDate(new Date().getTime() / 1000));

                self.uploadButton.unbind("click");
                self.uploadButton.on("click", function() {
                    var form = {
                        allowOverwrite: self.profileAllowOverwrite()
                    };

                    if (self.profileName() !== undefined) {
                        form["name"] = self.profileName();
                    }
                    if (self.profileDisplayName() !== undefined) {
                        form["displayName"] = self.profileDisplayName();
                    }
                    if (self.profileDescription() !== undefined) {
                        form["description"] = self.profileDescription();
                    }

                    data.formData = form;
                    data.submit();
                });
            },
            done: function(e, data) {
                self.fileName(undefined);
                self.placeholderName(undefined);
                self.placeholderDisplayName(undefined);
                self.placeholderDescription(undefined);
                self.profileName(undefined);
                self.profileDisplayName(undefined);
                self.profileDescription(undefined);
                self.profileAllowOverwrite(true);

                $("#settings_plugin_toggle_import").modal("hide");
                self.requestData();
            }
        });

        self.removeProfile = function(data) {
            self.profiles.removeItem(function(item) {
                return (item.key == data.key);
            });

            $.ajax({
                url:  API_BASEURL + "plugin/toggle",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "delete_profile",
                    key: data.key
                }),
                success: function() {
                    self.requestData();
                }
            });
        };

        self.makeProfileDefault = function(data) {
            _.each(self.profiles.items(), function(item) {
                item.isdefault(false);
            });
            var item = self.profiles.getItem(function(item) {
                return item.key == data.key;
            });
            if (item !== undefined) {
                item.isdefault(true);
            }

            $.ajax({
                url:  API_BASEURL + "plugin/toggle",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "use_profile",
                    default: true, 
                    key: data.key
                }),
                success: function() {
                    self.requestData();
                }
            });
        };

        self.showImportProfileDialog = function() {
            $("#settings_plugin_toggle_import").modal("show");
        };

        self.showEditLocalDialog = function() {
            $.ajax({
                url:  API_BASEURL + "plugin/toggle",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "get_local"
                }),
                success: function(data) {
                    $("#settings_plugin_toggle_textarea").val(data["data"]);
                }
            });
            $("#settings_plugin_toggle_editor").modal("show");
        };

        self.saveLocal = function() {
            $.ajax({
                url:  API_BASEURL + "plugin/toggle",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "save_local", 
                    data: $("#settings_plugin_toggle_textarea").val()
                }),
                success: function() {
                    $("#settings_plugin_toggle_editor").modal("hide");
                }
            });
        };


        self.restartToggle = function() {
            $.ajax({
                url:  API_BASEURL + "plugin/toggle",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "restart_toggle"
                }),
                success: function() {
                }
            });
        };

        self.requestData = function() {
            $.ajax({
                url: API_BASEURL + "plugin/toggle",
                type:"POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    "command": "get_profiles"
                }),
                success: self.fromResponse
            });
        };

        self.fromResponse = function(data) {
            var profiles = [];
            _.each(_.keys(data), function(key) {
                profiles.push({
                    key: key,
                    name: ko.observable(data[key].displayName),
                    description: ko.observable(data[key].description),
                    isdefault: ko.observable(data[key].default),
                    refs: {
                        resource: ko.observable(data[key].refs.resource),
                        download: ko.observable(data[key].refs.download)
                    }
                });
            });
            self.profiles.updateItems(profiles);
        };

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
            self.requestData();
        };

        self.onAfterBinding = function () {
        };
    }

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push([
        ToggleViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        "#settings_plugin_toggle"
    ]);
});
