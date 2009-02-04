require File.dirname(__FILE__) + "/rails_test_helper.rb"

describe MyMailer, :type => ActionMailer::TestCase do
  
  before do
    @expected.subject = 'MyMailer#confirm'
    @expected.body    = read_fixture('confirm')
    @expected.date    = Time.now
  end
  
  it "sends confirm mail" do
    MyMailer.create_confirm(@expected.date).encoded.should eql(@expected.encoded)
  end
  
  describe "nested context" do
    it "still sends confirm mail" do
      MyMailer.create_confirm(@expected.date).encoded.should eql(@expected.encoded)
    end
  end
end