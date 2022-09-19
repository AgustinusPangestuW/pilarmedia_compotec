odoo.define('vendor_rfq.main', function(require) {
	'use strict';

	var core = require('web.core');
	var _t = core._t;

	$(document).ready(
			function() {

				var dt = new Date();
				var yyyy = dt.getFullYear().toString();
				var mm = (dt.getMonth() + 1).toString(); // getMonth() is
															// zero-based
				var dd = dt.getDate().toString();
				var min = yyyy + '-' + (mm[1] ? mm : "0" + mm[0]) + '-'
						+ (dd[1] ? dd : "0" + dd[0]); // padding
				$('.input-date').prop('min', min);

				
				
				
				$('.input-qty').keyup(function(){
					var s = $(this).val()
					var original = $(this).val()
					if (s.length > 1){
						s = s.charAt(s.length-1)+"";
					}
					
					var myarr = ["0", "1", "2", "3" ,"4", "5", "6","7", "8", "9", "."];
					var exist = (myarr.indexOf(s) > -1);
					if (exist == true){
						$(this).val(original)
					}
					else{
						$(this).val(original.slice(0,-1))
					}
				});
				
				
				
//				Apply click
				$(".apply-rfq").click(function() {
					$('.apply-rfq').css('display', 'none')
					$('.div-submit').css('display', 'block')
					$("html, body").animate({
						scrollTop : 0
					}, "slow");
					//$('body').not("#id-div-submit").css("filter","blur(3px)");
				});
				
				
				
				
				$(".details-rfq").click(function() {
					$('.apply-rfq').css('display', 'none')
					$('.div-details').css('display', 'block')
					$("html, body").animate({
						scrollTop : 0
					}, "slow");
				});
				
				
				

				$(".apply-rfq3").click(function() {
					$('.apply-rfq').css('display', 'block')
					$('.div-submit').css('display', 'none')
					$('.div-details').css('display', 'none')
				});

				
				$(".error-dissmiss").click(function() {
					$('.error-msg').css('display', 'none')
				});
				
				
					
				$(".apply-rfq2").click(function() {
					$(".apply-rfq2").prop('disabled', true);
					var prices_data = ''
					$(".input-qty").each(function(){
						if(!$(this).val()){
							$("html, body").animate({
								scrollTop : 0
							}, 1);
							$('.error-msg').css('display', 'block')
							$(".apply-rfq2").prop('disabled', false);
							return false
						}
						prices_data = prices_data + $(this).attr('name')+":"+$(this).val()+","
				    });
					
					if (!$('#edate').val()){
						$("html, body").animate({
								scrollTop : 0
						}, 1);
						$('.error-msg').css('display', 'block')
						$(".apply-rfq2").prop('disabled', false);
						return false
					}
					
					$.ajax({
				        url : "/my/submit_rfq", 
						data: {
							price_units: prices_data,
							date: $('#edate').val(),
							note: $('#note').val(),
							id: $('#id').val(),
							},
						
						success : function(data) {
							$('.apply-rfq').css('display', 'none')
							$('.div-submit').css('display', 'none')
							$('.div-submited').css('display', 'block')
							alert("Thank you for submitting the Quotation.")
						},
						fail: function(data){
							$(".apply-rfq2").prop('disabled', false);
							$('.apply-rfq').css('display', 'block')
							$('.div-submit').css('display', 'none')
							$('.div-error').css('display', 'block')
						},
				    });
					$(".apply-rfq2").prop('disabled', false);
				});
				
				
				$('.select-class').on('change', function() {
					var state = this.value
					$("#id_vendor_state").val(state)
					$('.select-class').prop('disabled', true)
					$('#form-selection').submit()

			});
			});
});







