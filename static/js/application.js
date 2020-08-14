var ntdrt = ntdrt || {};

ntdrt.application = {

    logScrollEnabled: true,

    init: function () {
        var self = ntdrt.application;

        $(document).on('click', '[data-confirm]', function (e) {
            return confirm($(this).attr('data-confirm'));
        });

        $(document).on('click', '.toggle-navigation', function (e) {
            e.preventDefault();
            var target = $('.navbar > .container > .nav');
            if (target.is(':visible')) {
                target.slideUp(250);
            } else {
                target.slideDown(250);
            }
        });

        $(document).on('click', '.toggle-form', function (e) {
            e.preventDefault();
            var target = $('.navbar > .container > .navbar-form');
            if (target.is(':visible')) {
                target.slideUp(250);
            } else {
                target.slideDown(250);
            }
        });

        $(document).on('change', '.setup select[name="version"]', function (e) {
            var control = $(this);
            var version = control.val();
            if (version.indexOf('TC') === 0 && version.indexOf('USB') === -1) {
                $('.setup [data-serial]').hide();
                $('.setup [data-ble]').show();
            } else {
                $('.setup [data-serial]').show();
                $('.setup [data-ble]').hide();
            }
        });

        $(document).on('click', '.setup-link', function (e) {
            e.preventDefault();
            var link = $(this).attr('href');
            var parts = [];
            var data = self.collect_connection_data();
            for (var name in data) {
                parts.push(name + '=' + encodeURIComponent(data[name]));
            }
            var sep = link.indexOf('?') === -1 ? '?' : '&';
            window.location.href = link + sep + parts.join('&');
        });

        var logWrapper = $('#log');
        var previousLogPosition = 0;
        logWrapper.on('scroll', function () {
            var position = logWrapper.scrollTop();
            if (previousLogPosition > position) {
                self.logScrollEnabled = false;
            } else if (!self.logScrollEnabled) {
                var mostBottomPosition = logWrapper.find('pre').outerHeight(true) - logWrapper.height();
                if (position === mostBottomPosition) {
                    self.logScrollEnabled = true;
                }
            }
            previousLogPosition = position;
        });

        self.connection();
        self.log();
        self.current();

        self.graph();
    },

    socket: null,
    connection: function () {
        var self = this;
        var socket = self.socket = io.connect('http://' + document.domain + ':' + location.port);

        var newConnection = false;
        socket.on('connecting', function () {
            newConnection = false;
            $('#status').text('Connecting');
            self.disable(true);
            $('#connect button').text('Disconnect');
        });

        socket.on('connected', function () {
            newConnection = true;
            $('#status').text('Connected');
        });

        socket.on('disconnecting', function () {
            $('#status').text('Disconnecting');
        });

        socket.on('disconnected', function () {
            $('#status').text('Disconnected');
            self.disable(false);
            $('#connect button').text('Connect');
        });

        socket.on('update', function () {
            if (newConnection) {
                window.location.href = "/graph?name=";
            }
        });

        socket.on('log-error', function () {
            window.location.href = "/";
        });

        $(document).on('submit', '#connect', function (e) {
            var form = $(e.target);
            var input = form.find('[name="version"]');
            if (input.is(':disabled')) {
                socket.emit('close');
            } else {
                self.connect();
            }
            return false;
        });

        $(document).on('click', '.serial [data-connect]', function (e) {
            e.preventDefault();
            var port = $('.serial input[name="port"]').val();
            self.connect({port: port});
        });

        var serial = function () {
            socket.emit('scan_serial');
            $('.scan-result').text('Scanning... This can take a while...');
        };
        $(document).on('click', '.serial .scan button', serial);
        if ($('.serial .scan').length) {
            serial();
        }

        var ble = function () {
            socket.emit('scan_ble');
            $('.scan-result').text('Scanning... This can take a while...');
        };
        $(document).on('click', '.ble .scan button', ble);
        if ($('.ble .scan').length) {
            ble();
        }

        socket.on('scan-result', function (result) {
            $('.scan-result').html("<pre>" + result + "</pre>");
        });

        $(document).on('click', '.serial .scan-result [data-address]', function (e) {
            e.preventDefault();
            $('.scan-result').empty();
            self.connect({port: $(this).attr('data-address')});
        });

        $(document).on('click', '.ble .scan-result [data-address]', function (e) {
            e.preventDefault();
            $('.scan-result').empty();
            self.connect({ble_address: $(this).attr('data-address')});
        });
    },

    collect_connection_data: function () {
        var form = $('#connect');
        return {
            version: form.find('[name="version"]').val(),
            port: form.find('[name="port"]').val(),
            rate: form.find('[name="rate"]').val(),
            name: form.find('[name="name"]').val()
        };
    },

    connect: function (override) {
        var self = this;

        var data = self.collect_connection_data();
        if (override) {
            for (var name in override) {
                if (override.hasOwnProperty(name)) {
                    data[name] = override[name];
                }
            }

            var form = $('#connect');
            if (override.hasOwnProperty('port')) {
                form.find('[data-ble]').hide();
                var serial = form.find('[data-serial]');
                serial.show();
                serial.find('.setup-link').text(data['port']);

            } else if (override.hasOwnProperty('ble_address')) {
                form.find('[data-serial]').hide();
                var ble = form.find('[data-ble]');
                ble.show();
                ble.find('.setup-link').text(data['ble_address']);
            }
        }

        data = JSON.stringify(data);
        self.socket.emit('open', data);
        return data;
    },

    log: function () {
        var self = this;
        if ($('#log').length) {
            self.socket.on('log', function (message) {
                $('#log pre').append(message);
                if (self.logScrollEnabled) {
                    self.logScroll(500);
                }
            });

            $(window).on('resize', self.logResize);
            self.logResize();
            self.logScroll(0);
        }
    },

    chart: null,
    left_axis: null,
    right_axis: null,
    chart_buffer: [],
    current: function () {
        var self = this;
        var current = $('#current');
        if (current.length) {
            self.socket.on('update', function (message) {
                var data = JSON.parse(message);
                var counter = 0;
                current.find('td').each(function () {
                    $(this).text(data['table'][counter]);
                    counter++;
                });

                if (self.chart) {
                    self.chart_buffer.push(data);

                    // flush less often for huge datasets to minimize lag
                    var chart_size = self.chart.data.length;
                    var buffer_size = self.chart_buffer.length;
                    if (chart_size > 1000 && buffer_size < 5) {
                        return;
                    }
                    if (chart_size > 10000 && buffer_size < 10) {
                        return;
                    }
                    if (chart_size > 100000 && buffer_size < 60) {
                        return;
                    }

                    for (var index in self.chart_buffer) {
                        data = self.chart_buffer[index];
                        try {
                            var item = {
                                date: data['graph']['timestamp'],
                            };
                            var push = false;
                            if (self.left_axis && data['graph'].hasOwnProperty(self.left_axis)) {
                                item['left'] = data['graph'][self.left_axis];
                                push = true;
                            }
                            if (self.right_axis && data['graph'].hasOwnProperty(self.right_axis)) {
                                item['right'] = data['graph'][self.right_axis];
                                push = true;
                            }
                            if (push) {
                                self.chart.addData([item]);
                            }
                        } catch (e) {
                            // ignore
                        }
                    }
                    self.chart_buffer = [];
                }
            });
        }
    },

    graph: function () {
        var self = this;
        var chart = null;
        var graph = $('#graph');
        if (graph.length) {
            var create = function () {
                if (chart) {
                    chart.dispose();
                }

                graph.parent().find('.loading').show();

                var name = $('select[name="name"]').val();

                var left_axis = self.left_axis = $('select[name="left_axis"]').val();
                var left_name = $('#graph-settings option[value="' + left_axis + '"]').first().text();
                var right_axis = self.right_axis = $('select[name="right_axis"]').val();
                var right_name = $('#graph-settings option[value="' + right_axis + '"]').first().text();

                var unit = function (name) {
                    var matches = name.match(/\(([^)]+)\)/i);
                    if (matches) {
                        return matches[1];
                    }
                    return null;
                };
                var left_unit = unit(left_name);
                var right_unit = unit(right_name);

                var url = graph.attr('data-url');
                url += '?name=' + name;
                url += '&left_axis=' + left_axis;
                url += '&right_axis=' + right_axis;

                $.get(url, function (data) {
                    self.chart = chart = am4core.createFromConfig({
                        'data': data,
                        'xAxes': [{
                            'type': 'DateAxis',
                            'title': {
                                'text': 'Time',
                            }
                        }],
                        'yAxes': [
                            {
                                'id': 'leftAxis',
                                'type': 'ValueAxis',
                                'title': {
                                    'fill': 'rgb(229, 0, 0)',
                                    'text': left_name,
                                },
                                'numberFormatter': {
                                    'type': 'NumberFormatter',
                                    'numberFormat': '#.00 \' ' + left_unit + '\'',
                                    'forceCreate': true
                                },
                                'tooltip': {
                                    'disabled': true
                                },
                                'min': 0
                            },
                            {
                                'id': 'rightAxis',
                                'type': 'ValueAxis',
                                'title': {
                                    'fill': 'rgb(0, 128, 255)',
                                    'text': right_name,
                                },
                                'numberFormatter': {
                                    'type': 'NumberFormatter',
                                    'numberFormat': '#.00 \' ' + right_unit + '\'',
                                    'forceCreate': true
                                },
                                'tooltip': {
                                    'disabled': true
                                },
                                'renderer': {
                                    'opposite': true
                                },
                                'min': 0
                            }
                        ],
                        'series': [
                            {
                                'id': 'left',
                                'type': 'LineSeries',
                                'stroke': 'rgb(229, 0, 0)',
                                'strokeWidth': 2,
                                'dataFields': {
                                    'dateX': 'date',
                                    'valueY': 'left'
                                },
                                'tooltipText': '{left} ' + left_unit,
                                'tooltip': {
                                    'getFillFromObject': false,
                                    'background': {
                                        'fill': 'rgb(229, 0, 0)',
                                    },
                                    'label': {
                                        'fill': '#fff'
                                    }
                                }
                            },
                            {
                                'id': 'right',
                                'type': 'LineSeries',
                                'stroke': 'rgb(0, 128, 255)',
                                'strokeWidth': 2,
                                'dataFields': {
                                    'dateX': 'date',
                                    'valueY': 'right'
                                },
                                'yAxis': 'rightAxis',
                                'tooltipText': '{right} ' + right_unit,
                                'tooltip': {
                                    'getFillFromObject': false,
                                    'background': {
                                        'fill': 'rgb(0, 128, 255)',
                                    },
                                    'label': {
                                        'fill': '#fff'
                                    }
                                }
                            }
                        ],
                        'cursor': {
                            'type': 'XYCursor'
                        },
                    }, graph[0], 'XYChart');

                    chart.events.on('ready', function () {
                        graph.parent().find('.loading').hide();
                    });
                });
            };

            create();

            $(document).on('submit', '#graph-settings', function (e) {
                create();
                return false;
            });
        }
    },

    logScroll: function (delay) {
        var target = $('#log');
        target.animate({scrollTop: target.prop("scrollHeight")}, delay);
    },

    logResize: function () {
        var target = $('#log');
        var height = $(window).height();
        height -= $('body').height();
        height += target.height();
        target.css('height', height + 'px')
    },

    disable: function (value) {
        $('#connect select').prop('disabled', value);
        $('#connect input').prop('disabled', value);
    },

    register: function () {
        $(function () {
            ntdrt.application.init();
        });
    }
};

ntdrt.application.register();
