var ntdrt = ntdrt || {};

ntdrt.application = {

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
                window.location.href = "/graph?name=current";
            }
        });

        $(document).on('submit', '#connect', function (e) {
            var form = $(e.target);
            var input = form.find('[name="port"]');
            if (input.is(':disabled')) {
                socket.emit('close');
            } else {
                var data = {
                    version: form.find('[name="version"]').val(),
                    port: input.val(),
                    rate: form.find('[name="rate"]').val(),
                    name: form.find('[name="name"]').val()
                };
                data = JSON.stringify(data);
                socket.emit('open', data);
            }
            return false;
        });
    },

    log: function () {
        var self = this;
        if ($('#log').length) {
            self.socket.on('log', function (message) {
                $('#log').append(message);
                self.logScroll(500);
            });

            $(window).on('resize', self.logResize);
            self.logResize();
            self.logScroll(0);
        }
    },

    chart: null,
    left_axis: null,
    right_axis: null,
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
                                    'numberFormat': '#.00 \' ' + left_unit + '\''
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
                                    'numberFormat': '#.00 \' ' + right_unit + '\''
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
