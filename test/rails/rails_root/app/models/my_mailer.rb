class MyMailer < ActionMailer::Base
  

  def confirm(sent_at = Time.now)
    subject    'MyMailer#confirm'
    recipients ''
    from       ''
    sent_on    sent_at
    
    body       :greeting => 'Hi,'
  end

end
