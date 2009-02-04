require File.dirname(__FILE__) + "/rails_test_helper.rb"


describe "Stories", :type => ActionController::IntegrationTest do
  fixtures :all
  
  it "get my_models" do
    get my_models_path
    @response.should be_success
  end
  
  it "knows about fixtures" do
    my_models(:one).title.should == "MyString"
  end
  
  describe "nested context" do

    it "still get my_models" do
      get my_models_path
      @response.should be_success
    end

    it "still knows about fixtures" do
      my_models(:one).title.should == "MyString"
    end
  end
end
