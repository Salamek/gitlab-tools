$(function () {
    $('.select').select2();

    var per_page = 30;
    var $group_search = $(".group-search");
    $group_search.select2({
        ajax: {
            url: $group_search.data('source'),
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    q: params.term, // search term
                    page: params.page,
                    per_page: per_page
                };
            },
            processResults: function (data, params) {
                // parse the results into the format expected by Select2
                // since we are using custom formatting functions we do not need to
                // alter the remote JSON data, except to indicate that infinite
                // scrolling can be used
                params.page = params.page || 1;

                return {
                    results: data.items,
                    pagination: {
                        more: (params.page * per_page) < data.total
                    }
                };
            },
            cache: true
        },
        placeholder: 'Search for a group *',
        escapeMarkup: function (markup) { return markup; }, // let our custom formatter work
        minimumInputLength: 1,
        templateResult: function (group) {
            if (group.loading) {
                return group.text;
            }

            var markup = "<div class='select2-result-group clearfix'>" +
            "<div class='select2-result-group__avatar'><img src='" + group.avatar_url + "' /></div>" +
            "<div class='select2-result-group__meta'>" +
              "<div class='select2-result-group__title'>" + group.full_name + "</div>";

            if (group.description) {
                markup += "<div class='select2-result-group__description'>" + group.description + "</div>";
            }

            markup += "</div></div>";

            return markup;
        },
        templateSelection: function (group) {
            return group.full_name || group.text;
        }
    });

    if($group_search.length)
    {
        var group_url = $group_search.data('selected-url');
        if(group_url){
            $.ajax({
                type: 'GET',
                url: group_url
            }).then(function (data) {
                // create the option and append to Select2
                var option = new Option(data.full_name, data.id, true, true);
                $group_search.append(option).trigger('change');

                // manually trigger the `select2:select` event
                $group_search.trigger({
                    type: 'select2:select',
                    params: {
                        data: data
                    }
                });
            });
        }
    }

    var $project_search = $(".project-search");
    $project_search.select2({
        ajax: {
            url: $project_search.data('source'),
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    q: params.term, // search term
                    page: params.page,
                    per_page: per_page
                };
            },
            processResults: function (data, params) {
                // parse the results into the format expected by Select2
                // since we are using custom formatting functions we do not need to
                // alter the remote JSON data, except to indicate that infinite
                // scrolling can be used
                params.page = params.page || 1;

                return {
                    results: data.items,
                    pagination: {
                        more: (params.page * per_page) < data.total
                    }
                };
            },
            cache: true
        },
        placeholder: 'Search for a project',
        escapeMarkup: function (markup) { return markup; }, // let our custom formatter work
        minimumInputLength: 1,
        templateResult: function (project) {
            if (project.loading) {
                return project.text;
            }

            var markup = "<div class='select2-result-project clearfix'>" +
            "<div class='select2-result-project__avatar'><img src='" + (project.avatar_url || project.owner.avatar_url) + "' /></div>" +
            "<div class='select2-result-project__meta'>" +
            "<div class='select2-result-project__title'>" + project.name_with_namespace + "</div>";

            if (project.description) {
                markup += "<div class='select2-result-project__description'>" + project.description + "</div>";
            }

            markup += "<div class='select2-result-project__statistics'>" +
            "<div class='select2-result-project__forks'><i class='fa fa-code-fork'></i> " + project.forks_count + " Forks</div>" +
            "<div class='select2-result-project__stars'><i class='fa fa-star'></i> " + project.star_count + " Stars</div>" +
            "<div class='select2-result-project__issues'><i class='fa fa-exclamation'></i> " + project.open_issues_count + " Issues</div>" +
            "</div>" +
            "</div></div>";

            return markup;
        },
        templateSelection: function (project) {
            return project.name_with_namespace || project.text;
        }
    });

    if($project_search.length)
    {
        var project_url = $project_search.data('selected-url');
        if(project_url){
            $.ajax({
                type: 'GET',
                url: project_url
            }).then(function (data) {
                // create the option and append to Select2
                var option = new Option(data.name_with_namespace, data.id, true, true);
                $project_search.append(option).trigger('change');

                // manually trigger the `select2:select` event
                $project_search.trigger({
                    type: 'select2:select',
                    params: {
                        data: data
                    }
                });
            });
        }
    }

    var processAjaxError = function($xhr){
        var data = $xhr.responseJSON;
        if (data && 'message' in data)
        {
            alert(data.message);
        }
        else
        {
            alert('We are sorry but request failed. Check console for more information');
            console.log(e);
        }
    };

    var checkUrlFingerprint = function(check_url, add_url, fingerprint_url, success_callback, error_callback)
    {
        $.ajax({
            type: "POST",
            dataType: 'json',
            contentType: 'application/json',
            url: fingerprint_url,
            data: JSON.stringify({
                'url': check_url
            }),
            success: function(data){
                if (data.found)
                {
                    success_callback();
                }
                else
                {
                    prompt_result = prompt(
                    "The authenticity of host "+ data.hostname +" can't be established.\n" +
                    "MD5 Key fingerprint is:" + data.md5_fingerprint + ".\n" +
                    "SHA256 Key fingerprint is:" + data.sha256_fingerprint + ".\n" +
                    "Are you sure you want to add this fingerprint (yes/no)?"
                    );

                    if (prompt_result == "yes")
                    {
                        $.ajax({
                            type: "POST",
                            dataType: 'json',
                            contentType: 'application/json',
                            url: add_url,
                            data: JSON.stringify(data),
                            success: function(data){
                               success_callback();
                            },
                            error: processAjaxError
                        });
                    }
                    else
                    {
                        error_callback();
                        return;
                    }
                }
            },
            error: function($xhr){
                error_callback();
                processAjaxError($xhr);
            }
        });
    };

    $('.check-signature').each(function(){
        var $input = $(this);
        var $form = $input.closest('form');
        var fingerprint_url = $input.data('fingerprint-url');
        var gitlab_url = $input.data('gitlab-url');
        var add_url = $input.data('fingerprint-add-url');
        $form.submit(function(e){
            e.preventDefault();

            var data = $input.val();
            if (!data)
            {
                alert('No data');
                return;
            }

            $loaderIcon = $('<i class="fa fa-spinner fa-spin"></i>');
            $form.find('button[type="submit"]').prepend($loaderIcon)
            checkUrlFingerprint(gitlab_url, add_url, fingerprint_url, function(){
                checkUrlFingerprint($input.val().trim(), add_url, fingerprint_url, function(){
                    $loaderIcon.remove();
                    $form.unbind().submit();
                }, function(){
                    $loaderIcon.remove();
                });
            }, function(){
                $loaderIcon.remove();
            });
        });
    });

    $('.confirm').click(function(e){
        var message = $(this).data('confirm-message');
        if (!confirm(message))
        {
            e.preventDefault();
        }
    });

    $('.date').each(function(){
        $(this).datetimepicker({
            format: 'DD.MM.YYYY HH:mm'
        });
    });

    $('[data-toggle="popover"]').popover();
    $('.has-error .form-control').first().focus();

    /**
   * Allow anchored tabs
   */
    //Support for urling tabs
    var url = document.location.toString();
    if (url.match('#')) {
        $('.nav-tabs a[href=#'+url.split('#')[1]+']').tab('show') ;
    }

    // Change hash for page-reload
    $('.nav-tabs a').on('shown.bs.tab', function (e) {
        window.location.hash = e.target.hash;
    });

    $('#tracebackModal').on('show.bs.modal', function (event) {
        var button = $(event.relatedTarget);
        var traceback_url = button.data('traceback-url');
        var modal = $(this);
        $.ajax({
            type: "GET",
            dataType: 'json',
            contentType: 'application/json',
            url: traceback_url,
            success: function(data){
                modal.find('.modal-body pre').html(data.traceback)
            }
        });
    });
 });
