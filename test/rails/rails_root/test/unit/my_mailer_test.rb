require 'test_helper'

class MyMailerTest < ActionMailer::TestCase
  test "confirm" do
    @expected.subject = 'MyMailer#confirm'
    @expected.body    = read_fixture('confirm')
    @expected.date    = Time.now

    assert_equal @expected.encoded, MyMailer.create_confirm(@expected.date).encoded
  end

end
