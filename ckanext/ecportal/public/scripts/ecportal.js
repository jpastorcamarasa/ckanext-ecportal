(function ($) {
	$(function () {
		var arrow_url = CKAN.SITE_URL_NO_LOCALE + '/images/arrow_{0}.gif';
		var dropdown = $('#language-selector ul');
		var dropdown_image = $('#language-selector .root img');
		dropdown
			.bind('mouseleave', function() {
				_dropdown(false);
			})
			.parent()
			.bind('click', function() {
				_dropdown(true);
			});
		function _dropdown($show) {
			if ($show) {
				dropdown.fadeIn();
				dropdown_image.attr('src', arrow_url.replace('{0}', 'up'));
			} else {
				dropdown.slideUp();
				dropdown_image.attr('src', arrow_url.replace('{0}', 'down'));
			}
		}

		if ($('#more-meta dl').length > 0) {
			$('.more-meta a').bind('click', function() {
				$('.more-meta').hide();
				$('.less-meta').show();
				$('#more-meta').show();
			});
			$('.less-meta a').bind('click', function() {
				$('.less-meta').hide();
				$('.more-meta').show();
				$('#more-meta').hide();
			});
		} else {
			$('.more-meta').hide();
		}

		function sortby_dropdown() {
			$('select[name="sort"]').on('change', function() {
				$('input[name="sort"]').val($(this).val());
				$('.page-search form').trigger('submit');
			});
		}
		sortby_dropdown();

    // last-updated date
    $.ajax({
      url : '/api/getUpdatedDate',
      dataType: 'json',
      timeout : 1000
    }).done(function (data){
      $("#content-last-updated").text(data.lastUpdate);
    });
	});
}(jQuery));
